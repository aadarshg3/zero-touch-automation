
while(True):
    ip = input("Enter your ip address:")

    if ip.startswith("10."):
        print("Class A private ip")
    elif ip.startswith("172.") and float(ip[4:7]) >= 16. and float(ip[4:7]) <= 31.:
        print("CLass B Prvate ip")
    elif ip.startswith("192.168"):
        print("Class C Private ip")
    else:
        print("Not private ip")
        
    choice = input("Do you want to continue (Y/N):")
    # if (choice != "Y") or (choice != "y"):
    #     print(choice)
    #     break
    if (choice == "Y") or (choice == "y"):
        print(choice)
        continue
    else:
        break
