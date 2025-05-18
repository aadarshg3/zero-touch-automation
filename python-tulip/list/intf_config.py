# List of devices, customers, sites, and interfaces
device_list = ["sw1", "sw2", "sw3"]
cust_list = ["cus_x", "cus_y", "cus_z"]
site_list = ["site_A", "site_B", "site_C"]
intf_list = ["gig0/1", "gig0/2", "gig0/3", "gig0/4"]

# Port configuration templates
access_port_config_list = [
    "switch mode access",
    "switchport access vlan 10"
]

trunk_port_config_list = [
    "switch mode trunk",
    "switchport trunk allowed vlan add 10"
]

# Begin configuration
for cust in cust_list:
    print(f"\n============== Configuring for {cust} =============>\n")

    for site in site_list:
        print(f"$$$$$$  Configuring {site}  $$$$$$\n")

        for device in device_list:
            print(f"--- Configuring device: {device} ---\n")

            for intf in intf_list:
                print(f"interface {intf}")

                # Apply trunk configuration to first two interfaces
                if intf in ["gig0/1", "gig0/2"]:
                    for config in trunk_port_config_list:
                        print(config)
                else:
                    for config in access_port_config_list:
                        print(config)

            print()  # Add a blank line after each device config

















# device_list = ["sw1", "sw2", "sw3"]
# cust_list = ["cus_x", "cus_y", "cus_z"]
# site_list = ["site_A", "site_B", "site_C"]
# intf_list = ["gig0/1", "gig0/2", "gig0/3", "gig0/4"]
# access_port_config_list =  ["switch mode access", "switchport access vlan 10"]
# trunk_port_config_list = ["switch mode trunk", "switchport trunk allowed vlan add 10"]


# for cust in cust_list:
#     print(f"\n==============Configuring for {cust}=============>")
#     for site in site_list:
#         print(f"\n$$$$$$  Configuring {site}   $$$$$$")
#         for device in device_list:
#             print(f"\nConfiguring device {device}...\n")
#             for intf in intf_list:
#                 if intf == "gig0/1" or intf == "gig0/2":
#                     print(f"interface {intf}")
#                     for config in trunk_port_config_list:
#                         print(config)
#                 else:
#                     print(f"interface {intf}")
#                     for config in access_port_config_list:
#                         print(config)
