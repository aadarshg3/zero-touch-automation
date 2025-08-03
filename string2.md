## 🔹 String's Method : upper
**🧠 Code:**
```python
s = "hello world"
print(s.upper())  # Convert to uppercase
```
**📤 Output:**
```text
HELLO WORLD
```
**🧠 Code:**
```python
intf_name = "GigabitEthernet0/1"

if intf_name == "GIGABITETHERNET0/1":
    print("Interface found")
else:
    print("Interface NOT found")

if intf_name.upper() == "GIGABITETHERNET0/1":
    print("Interface found")

if intf_name.lower() == "gigabitethernet0/1":
    print("Interface found")
```
**📤 Output:**
```text
Interface NOT found
Interface found
Interface found
```
## 🔹 Indexing and Advanced Slicing
**🧠 Code:**
```python
device = "ROUTER"

# Fetch by index
print(device[0])     # 'R'
print(device[3])     # 'T'

# Negative indexing
print(device[-1])    # 'R'
print(device[-2])    # 'E'

# Slicing
print(device[1:4])   # 'OUT'
print(device[:3])    # 'ROU'
print(device[2:])    # 'UTER'

# Step slicing
print(device[::2])   # 'RUE'
print(device[1::2])  # 'OTR'

# Reversing
print(device[::-1])      # 'RETUOR'
print(device[-1::-2])    # 'RTE'
print(device[5:1:-1])    # 'RETU'
```
## 🔹 String Concatenation
**🧠 Code:**
```python
vlan = "vlan"
vlan_id = "10"
result = vlan + vlan_id
print(result)

vlan_name = "Accounting"
result = vlan + " " + vlan_name
print(result)

# Common Error
vlan_id = 10
# result = vlan + vlan_id  # ❌ TypeError
result = vlan + str(vlan_id)  # ✅ Correct
print(result)
```
**📤 Output:**
```text
vlan10
vlan Accounting
vlan10
```
## 🔹 Typecasting Examples
**🧠 Code:**
```python
# Example 1: String to int
vlan_id_str = "20"
vlan_id_int = int(vlan_id_str)
if vlan_id_int > 1 and vlan_id_int < 4095:
    print("Valid VLAN ID")

# Example 2: int to string for hostname
device_id = 5
hostname = "Router" + str(device_id)
print(hostname)

# Example 3: list to comma-separated string
ip_list = ["192.168.1.1", "192.168.1.2"]
ip_string = ", ".join(ip_list)
print("Devices found at: " + ip_string)
```
**📤 Output:**
```text
Valid VLAN ID
Router5
Devices found at: 192.168.1.1, 192.168.1.2
```
## 🔹 IP Classification Using String Methods
**🧠 Code:**
```python
while True:
    ip = input("Enter an IP address: ")
    parts = ip.split('.')
    if len(parts) != 4:
        print("Invalid format")
        continue

    if all(part.isdigit() for part in parts):
        p1, p2, p3, p4 = map(int, parts)
        if not all(0 <= p <= 255 for p in [p1, p2, p3, p4]):
            print("Invalid range")
        elif p1 == 10:
            print(f"{ip} is Class A Private")
        elif p1 == 172 and 16 <= p2 <= 31:
            print(f"{ip} is Class B Private")
        elif p1 == 192 and p2 == 168:
            print(f"{ip} is Class C Private")
        elif p1 == 127:
            print(f"{ip} is a Loopback Address")
        else:
            print(f"{ip} is a Public IP")
    else:
        print("Invalid input")

    if input("Continue? (yes/no): ").lower() != "yes":
        break
```
**📤 Output:**
```text
Enter an IP address: 192.168.2.1
192.168.2.1 is Class C Private
...
Exiting the program.
```
