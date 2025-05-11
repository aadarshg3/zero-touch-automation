
vlan = input("Enter vlan:")
vlan_name = input("Enter vlan name:")

# vlan_syntax = """vlan {} \n name {}"""
# vlan_config = vlan_syntax.format(vlan, vlan_name)
# print(vlan_config)

vlan_config = f"vlan {vlan} \n name {vlan_name}"
print(vlan_config)


- take ip as an input from user
- check if it has 4 octets
- check if each octet has value between 0-255
- find the class of a given ip.

interface config generation
interface name
bandwith
speed
description

'isdecimal', 'isdigit', isnumeric()
