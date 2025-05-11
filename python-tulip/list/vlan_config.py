vlan_list = [10, 20, 30, 40]
device_list = ["sw1", "sw2", "sw3"]
site_list = ["site_A", "site_B", "site_C"]

for site in site_list:
    print(f"\nConfiguring Vlan on {site}============>")
    for device in device_list:
        print(f"\nConnecting to {device}...\n")
        for vlan in vlan_list:
            print(f"vlan {vlan}")
            print(f" name vlan_{vlan}")


