# 🧵 String data type

## 🔹 How to define a "string"

**🧠 Code:**
```python
# Different ways to create strings
single_quoted = 'Hello'
double_quoted = "World"
multi_line = '''This is 
NetG India's 
Python Class'''
```

## 🔹 What is the data type of python? And, What is memory location? 

**🧠 Code:**
```python
box = "Apple"
print(box)             # prints the string
print(type(box))       # shows the type is str
```
**📤 Output:**
```text
Apple
<class 'str'>
```

## 🔹 Invalid Assignments (Errors)

**🧠 Code:**
```python
# These are incorrect and will throw errors
"apple" = box              # ❌ Cannot assign to literal
print(undefined_box)       # ❌ Variable not defined
```
**📤 Output:**
```text
SyntaxError: can't assign to literal
NameError: name 'undefined_box' is not defined
```

## 🔹 Valid Assignment

**🧠 Code:**
```python
box = "apple"
print(box)  # ✅ Correct assignment
```
**📤 Output:**
```text
apple
```

## 🔹 Memory Address Demo

**🧠 Code:**
```python
salt_box = "Salt"
sugar_box = "Sugar"

# Display memory addresses (ids)
print(id(salt_box))
print(id(sugar_box))
```
**📤 Output:**
```text
Value of salt_box: Salt
Memory address of salt_box: 140448083084848

Value of sugar_box: Sugar
Memory address of sugar_box: 140448083084976
```

## 🔹 Positive and Negative Indexing

**🧠 Code:**
```python
box = "Sugar"
print(box[0])   # 'S'
print(box[-1])  # 'r'
```
**📤 Output:**
```text
S
r
```

## 🔹 How to Slice String? 

**🧠 Code:**
```python
python = "This_is_NetG_India"
print(python[0:4])   # 'This'
print(python[8:12])  # 'NetG'
print(python[-5:])   # 'India'
```
**📤 Output:**
```text
This
NetG
India
```

## 🔹 How can slice using step (jump) & How to get string in reverse? 

**🧠 Code:**
```python
print(python[::2])    # every second char
print(python[::-1])    # reversed string
```
**📤 Output:**
```text
Ti_sNt_nda
aidnI_GteN_si_sihT
```

## 🔹 In Python how to take help to understand the method of data structure? 

**🧠 Code:**
```python
print(dir(str))       # Lists all string methods
help(str.upper)         # Help on upper method
```

## 🌐 Examples of Format method!

## 🔹 Ex:1) Ping Command

**🧠 Code:**
```python
ping_cmd = "ping {} source {}"
print(ping_cmd.format("2.2.2.2", "1.1.1.1"))
```
**📤 Output:**
```text
ping 2.2.2.2 source 1.1.1.1
```

## 🔹 Ex:2) VLAN Command

**🧠 Code:**
```python
vlan_cmd = "vlan {}"
print(vlan_cmd.format(10))
```
**📤 Output:**
```text
vlan 10
```

## 🔹 Ex:3) SNMP Config

**🧠 Code:**
```python
snmp_cmd = "snmp-server host {} {} {}"
print(snmp_cmd.format("1.1.1.1", "public", "link-down"))
```
**📤 Output:**
```text
snmp-server host 1.1.1.1 public link-down
```

## 🔹 Ex:4) DNS Config

**🧠 Code:**
```python
dns_cmd = "ip name-server {}"
print(dns_cmd.format("8.8.8.8"))
```
**📤 Output:**
```text
ip name-server 8.8.8.8
```

## 🔹 Ex:5) User Account

**🧠 Code:**
```python
cmd1 = "username {} privilege {} password {}"
print(cmd1.format("admin", "15", "netg"))
```
**📤 Output:**
```text
username admin privilege 15 password netg
```

## 🔹 Ex:6) NTP Server

**🧠 Code:**
```python
ntp_cmd = "ntp server {}"
print(ntp_cmd.format("server 0.in.pool.ntp.org"))
```
**📤 Output:**
```text
ntp server server 0.in.pool.ntp.org
```
