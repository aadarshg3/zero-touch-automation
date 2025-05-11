ip = input("Enter the IP address: ")  # Take the IP address input as a string

# Check the private IP ranges and class types
if ip.startswith("10."):
    print(f"{ip} is a private IP of Class A.")
elif ip.startswith("192.168."):
    print(f"{ip} is a private IP of Class C.")
elif ip.startswith("172.") and (ip[4:6] >= "16" and ip[4:6] <= "31"):
    print(f"{ip} is a private IP of Class B.")
else:
    print(f"{ip} is not a private IP.")
