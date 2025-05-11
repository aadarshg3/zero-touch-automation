while True:
    # Ask user to enter an IP address
    ip = input("Enter an IP address: ")

    # Split the IP into 4 parts
    parts = ip.split('.')  # e.g. '192.168.1.1' → ['192', '168', '1', '1']

    # Step 1: Check if IP has exactly 4 parts
    if len(parts) != 4:
        print("Invalid IP address format - must have 4 parts separated by dots.")
    else:
        valid = True

        # Step 2: Check if each part is a digit
        for part in parts:
            if not part.isdigit():
                valid = False
                print("Invalid IP address - contains non-numeric values.")
                break

        if valid:
            # Convert parts to integers
            p1 = int(parts[0])
            p2 = int(parts[1])
            p3 = int(parts[2])
            p4 = int(parts[3])

            # Step 3: Check if values are between 0 and 255
            if not (0 <= p1 <= 255):
                print("Invalid IP - first part out of range.")
            elif not (0 <= p2 <= 255):
                print("Invalid IP - second part out of range.")
            elif not (0 <= p3 <= 255):
                print("Invalid IP - third part out of range.")
            elif not (0 <= p4 <= 255):
                print("Invalid IP - fourth part out of range.")
            else:
                # Step 4: Classify the IP address
                if p1 == 10:
                    print(ip + " is a Private IP of Class A")
                elif p1 == 172 and 16 <= p2 <= 31:
                    print(ip + " is a Private IP of Class B")
                elif p1 == 192 and p2 == 168:
                    print(ip + " is a Private IP of Class C")
                elif p1 == 127:
                    print(ip + " is a Loopback Address")
                elif 224 <= p1 <= 239:
                    print(ip + " is a Class D (Multicast) IP Address")
                elif 240 <= p1 <= 255:
                    print(ip + " is a Class E (Experimental) IP Address")
                else:
                    print(ip + " is a Public IP Address")

    # Ask user if they want to continue
    answer = input("Would you like to continue? (yes/no): ")
    if answer.lower() != "yes":
        print("Exiting the program.")
        break

