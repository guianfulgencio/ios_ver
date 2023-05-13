"""
Script to check if there are abnormal reboot for Cisco routers, switches and voice gateways

Applicable only for IOS/IOS-XE, NXOS devices

Workflow:
    - Clean the device inventory (device_list.csv) that has been captured from Solarwinds Query.
    - Once we have the valid and supported device from raw inventory, we will access each devices
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pandas as pd
from napalm import get_network_driver
from rich import print as rprint



##########################
# Global Variables
##########################
#username = args.username
#password = args.password
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
    return data_frame

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
        results_frame = results_frame.append(region_dev_frame)
        
    now = datetime.now()
    report_name = f"New_device_list.csv"
    #results_frame = region_dev_frame
    #results_frame = results_frame.sort_values(by=["Region", "Device Name"], ascending=(True, True))
    results_frame.to_csv(report_name, index=False)
    rprint(f"✅ {report_name} - Successfully generated!")

##########################
# Run Script
##########################
if __name__ == "__main__":
    main()
