# 📘 Python Strings and Networking - Practical Guide
This guide covers the fundamentals of strings in Python, including creation, manipulation, method usage, and real-world networking examples.

## 🔹 String Basics
In Python, a **string** is an immutable sequence of Unicode characters.
They can be created using single (`'`), double (`"`), or triple (`'''` or `"""`) quotes for multi-line strings.

**🧠 Code:**
```python
# String creation
single_quoted = 'Hello'
double_quoted = "World"
multi_line = '''This is 
NetG India's 
Python Class'''
```
## 🔹 Memory and Assignment
**🧠 Code:**
```python
box = "Apple"
print(box)
print(type(box))
```
**📤 Output:**
```text
Apple
<class 'str'>
```
**🧠 Code (Incorrect Assignment):**
```python
"apple" = box  # ❌ SyntaxError
print(undefined_box)  # ❌ NameError
```
**📤 Output:**
```text
SyntaxError: can't assign to literal
NameError: name 'undefined_box' is not defined
```
**🧠 Code (Correct Assignment):**
```python
box = "apple"
print(box)
```
**📤 Output:**
```text
apple
```
**🧠 Code (Memory Address):**
```python
salt_box = "Salt"
sugar_box = "Sugar"
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
## 🔹 Indexing and Slicing
### Positive and Negative Indexing
**🧠 Code:**
```python
box = "Sugar"
print(box[0])
print(box[1])
print(box[2])
print(box[3])
print(box[4])
print(box[-1])
print(box[-2])
print(box[-3])
print(box[-4])
print(box[-5])
```
**📤 Output:**
```text
S
u
g
a
r
r
a
g
u
S
```
**🧠 Code (Slicing Examples):**
```python
python = "This_is_NetG_India"
print(python[0:4])
print(python[5:7])
print(python[8:12])
print(python[-5:])
print(python[::2])
print(python[::-1])
```
**📤 Output:**
```text
This
is
NetG
India
Ti_sNt_nda
aidnI_GteN_si_sihT
```
## 🔹 Inspecting Methods
**🧠 Code:**
```python
dir(str)
```
**📤 Output:**
```text
['__add__', '__class__', ..., 'zfill']
```
**🧠 Code:**
```python
help(str.upper)
```
**📤 Output:**
```text
Help on method_descriptor: upper(...) -> str
Return a copy of the string converted to uppercase.
```
## 🔹 Networking Examples with `format()`
### 📌 Ping Command
**🧠 Code:**
```python
ping_cmd = "ping {} source {}"
print(ping_cmd.format("2.2.2.2", "1.1.1.1"))
```
**📤 Output:**
```text
ping 2.2.2.2 source 1.1.1.1
```
### 📌 VLAN Command
**🧠 Code:**
```python
vlan_cmd = "vlan {}"
print(vlan_cmd.format(10))
```
**📤 Output:**
```text
vlan 10
```
### 📌 SNMP Config
**🧠 Code:**
```python
snmp_cmd = "snmp-server host {} {} {}"
print(snmp_cmd.format("1.1.1.1", "public", "link-down"))
```
**📤 Output:**
```text
snmp-server host 1.1.1.1 public link-down
```
### 📌 DNS Config
**🧠 Code:**
```python
dns_cmd = "ip name-server {}"
print(dns_cmd.format("8.8.8.8"))
```
**📤 Output:**
```text
ip name-server 8.8.8.8
```
### 📌 User Account
**🧠 Code:**
```python
cmd1 = "username {} privilege {} password {}"
print(cmd1.format("admin", "15", "netg"))
```
**📤 Output:**
```text
username admin privilege 15 password netg
```
### 📌 NTP Server
**🧠 Code:**
```python
ntp_cmd = "ntp server {}"
print(ntp_cmd.format("server 0.in.pool.ntp.org"))
```
**📤 Output:**
```text
ntp server server 0.in.pool.ntp.org
```