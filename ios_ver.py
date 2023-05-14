"""
Script to check if there are abnormal reboot for Cisco routers, switches and voice gateways

Applicable only for IOS/IOS-XE, NXOS devices

Workflow:
    - Clean the device inventory (device_list.csv) that has been captured from Solarwinds Query.
    - Once we have the valid and supported device from raw inventory, we will access each devices
      via SSH and parse the reload reason from "show version" output.
    - Generate CSV report for devices with unknown/abnormal reboot reason.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pandas as pd
from napalm import get_network_driver
from rich import print as rprint


##########################
# Script Arguments
##########################
parser = argparse.ArgumentParser(description="Check device reboot reason")
parser.add_argument('-u', '--username', type=str, metavar='',\
    help='Username to access network device', required=True)
parser.add_argument('-p', '--password', type=str, metavar='',\
    help='Password to access network device', required=True)
args = parser.parse_args()


##########################
# Global Variables
##########################
username = args.username
password = args.password
results_frame = pd.DataFrame()
SW_REPORT_FILE = "./device_list.csv"


#############################
# Get only supported devices
#############################
def get_supported_devices(solarwinds_results, region):
    '''
    Capture only the supported devices(IOS/IOS-XE/NXOS) from Solarwinds device query report
        - solarwinds_results => csv report that was generated from
                                get_device_list_from_all_region.py script (device_list.csv)
    '''
    unsupported_devices = [
        "Cisco Unified Communications Manager",
        "WLC",
        "Wireless",
        "Air",
        "AIR",
        "WsSvcFwm1sc",
        "ASA"
    ]
    rprint(f"[yellow]Getting supported devices from {solarwinds_results}...[/yellow]")
    data_frame = pd.read_csv(solarwinds_results)
    data_frame = data_frame[data_frame.Region == region].sort_values(by="Device Name",\
                ascending=True)
    data_frame = data_frame[~data_frame["Model"].str.contains('|'.join(unsupported_devices))]
    data_frame["ios version"] = ""
    return data_frame


##########################
# Get reboot reason via SSH
##########################
def get_reboot_reason(device_data):
    '''
    Access device via SSH and get reboot reason
        - device_data = pandas series data
    '''
    global results_frame
    hostname = device_data["Device Name"]
    ip_address = device_data["IP Address"]
    os_ver = "nxos_ssh" if "Nexus" in device_data["Model"] else "ios"
    cli_command = ["show ver | inc NX-OS" if os_ver == 'nxos_ssh' else "show ver | inc IOS XE"]
    driver = get_network_driver(os_ver)
    device = driver(
        hostname=ip_address,
        username=username,
        password=password
    )

    try:
        device.open()
        cli_output = device.cli(cli_command)
        ios_version = cli_output[cli_command[0]].replace("Operating System (NX-OS) Software", "")
        ios_version = ios_version.split(',')[0]
        device_data["ios version"] = ios_version.strip()
        device.close()
        rprint(f"✅ {hostname} :: {ios_version}")
    except Exception as err:
        device_data["Error"] = err
        rprint(f"❌ {hostname} :: {err}")

    results_frame = results_frame.append(device_data)


##########################
# Main Script
##########################
def main():
    '''
    Main Script
    '''
    global results_frame
    for region in ["US", "EMEA", "APAC"]:
        rprint(f"{'#'*7} PROCESSING {region} {'#'*7}")
        region_dev_frame = get_supported_devices(SW_REPORT_FILE, region)
        region_devices = [device for _, device in region_dev_frame.iterrows()]
        with ThreadPoolExecutor(max_workers=100) as executor:
            executor.map(get_reboot_reason, region_devices)

    now = datetime.now()
    report_name = f"report {now.strftime('%d-%b-%Y')}.csv"
    results_frame = results_frame[results_frame["ios version"] != ""]
    results_frame = results_frame.sort_values(by=["Region", "Device Name"], ascending=(True, True))
    results_frame.to_csv(report_name, index=False)
    rprint(f"✅ {report_name} - Successfully generated!")


##########################
# Run Script
##########################
if __name__ == "__main__":
    main()
