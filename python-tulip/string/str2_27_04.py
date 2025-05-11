# User input for IP address
ip = input("Enter an IP address: ")

# Check if the IP address contains exactly three dots (.)
if ip.count('.') != 3:
    print("Invalid IP address")
else:
    # Find positions of dots in the IP address
    dot1 = ip.find('.')
    dot2 = ip.find('.', dot1 + 1)
    dot3 = ip.find('.', dot2 + 1)

    # Extract each part of the IP address by slicing the string
    part1 = ip[:dot1]
    part2 = ip[dot1 + 1:dot2]
    part3 = ip[dot2 + 1:dot3]
    part4 = ip[dot3 + 1:]

    # Validate each part to ensure it is a number between 0 and 255
    if not (part1.isdigit() and part2.isdigit() and part3.isdigit() and part4.isdigit()):
        print("Invalid IP address - non-numeric characters found.")
    else:
        part1 = int(part1)
        part2 = int(part2)
        part3 = int(part3)
        part4 = int(part4)

        # Check if each part is between 0 and 255
        if not (0 <= part1 <= 255 and 0 <= part2 <= 255 and 0 <= part3 <= 255 and 0 <= part4 <= 255):
            print("Invalid IP address - values must be between 0 and 255.")
        else:
            # Check if the IP is private
            if part1 == 10:  # 10.0.0.0 - 10.255.255.255
                print(f"The IP address {ip} is a Private IP.")
            elif part1 == 172 and 16 <= part2 <= 31:  # 172.16.0.0 - 172.31.255.255
                print(f"The IP address {ip} is a Private IP.")
            elif part1 == 192 and part2 == 168:  # 192.168.0.0 - 192.168.255.255
                print(f"The IP address {ip} is a Private IP.")
            else:
                print(f"The IP address {ip} is a Public IP.")

