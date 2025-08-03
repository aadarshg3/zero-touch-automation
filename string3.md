# 🌐 IP Address Classification in Python
This document demonstrates how to classify IP addresses as **private**, **public**, or **special types** using string operations in Python. Includes step-by-step logic and terminal interaction examples.

## 🔹 LOGIC 1: Using `startswith()` and basic string slicing
**🧠 Code:**
```python
num = 1
while(num <= 10):
    ip = input("Enter your ip:").strip().split(".")
    print(ip)
    if ip.startswith("10."):
        print("CLass A private ip address")
    elif ip.startswith("192.168."):
        print("CLass C private ip address")
    elif ip.startswith("172") and float(ip[4:7]) >= 16. and float(ip[4:7]) <= 31.:
        print("Class B private ip")
    else:
        print("NOT a private ip")   
    
    choice = input("Do you want to continue (Y/N):")
    if choice.upper() != "Y":
        break
    num = num + 1

print("after exit")
```
## 🔹 LOGIC 2: Strictly using string methods
**🧠 Code:**
```python
while(True):  # keep asking values 
    ip = input("Enter an IP address: ")

    if ip.count('.') != 3:
        print("Invalid IP address")
    else:
        dot1 = ip.find('.')
        dot2 = ip.find('.', dot1 + 1)
        dot3 = ip.find('.', dot2 + 1)

        part1 = ip[:dot1]
        part2 = ip[dot1 + 1:dot2]
        part3 = ip[dot2 + 1:dot3]
        part4 = ip[dot3 + 1:]

        if not (part1.isdigit() and part2.isdigit() and part3.isdigit() and part4.isdigit()):
            print("Invalid IP address - non-numeric characters found.")
        else:
            part1 = int(part1)
            part2 = int(part2)
            part3 = int(part3)
            part4 = int(part4)

            if not (0 <= part1 <= 255 and 0 <= part2 <= 255 and 0 <= part3 <= 255 and 0 <= part4 <= 255):
                print("Invalid IP address - values must be between 0 and 255.")
            else:
                if part1 == 10:
                    print(f"The IP address {ip} is a Private IP.")
                elif part1 == 172 and 16 <= part2 <= 31:
                    print(f"The IP address {ip} is a Private IP.")
                elif part1 == 192 and part2 == 168:
                    print(f"The IP address {ip} is a Private IP.")
                else:
                    print(f"The IP address {ip} is a Public IP.")
    
    choice = input("Do you want to continue (Y/N): ")
    if choice != "Y":
        break

print("after exit")
```
**📤 Terminal Output Example:**
```text
(venv) [string]$ python3 ip_check_str.py 
Enter an IP address: 192.1.1.1
The IP address 192.1.1.1 is a Public IP.
Do you want to continue (y/n): y
Enter an IP address: 172.14.4.4
The IP address 172.14.4.4 is a Public IP.
Enter an IP address: 182.1.2.2
The IP address 182.1.2.2 is a Public IP.
Enter an IP address: 172.16.3.4
The IP address 172.16.3.4 is a Private IP.
Enter an IP address: 182.2.2.2
The IP address 182.2.2.2 is a Public IP.
(venv) [string]$ 
```
## 🔹 LOGIC 3: IP Address Classification with Proper Validation
**🧠 Code:**
```python
while True:
    ip = input("Enter an IP address: ")
    parts = ip.split('.')

    if len(parts) != 4:
        print("Invalid IP address format - must have 4 parts separated by dots.")
    else:
        valid = True
        for part in parts:
            if not part.isdigit():
                valid = False
                print("Invalid IP address - contains non-numeric values.")
                break

        if valid:
            p1 = int(parts[0])
            p2 = int(parts[1])
            p3 = int(parts[2])
            p4 = int(parts[3])

            if not (0 <= p1 <= 255):
                print("Invalid IP - first part out of range.")
            elif not (0 <= p2 <= 255):
                print("Invalid IP - second part out of range.")
            elif not (0 <= p3 <= 255):
                print("Invalid IP - third part out of range.")
            elif not (0 <= p4 <= 255):
                print("Invalid IP - fourth part out of range.")
            else:
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

    answer = input("Would you like to continue? (yes/no): ")
    if answer.lower() != "yes":
        print("Exiting the program.")
        break
```
**📤 Output Example:**
```text
Enter an IP address: 192.168.2.1 
192.168.2.1 is a Private IP of Class C
Enter an IP address: 182.6.6.6
182.6.6.6 is a Public IP Address
Enter an IP address: 192.1688.1.1
Invalid IP - second part out of range.
Enter an IP address: 10.1.1.1
10.1.1.1 is a Private IP of Class A
Exiting the program.
```