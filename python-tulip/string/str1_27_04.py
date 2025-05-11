# Generate config for:
# SNMP config: SNMP config syntax:
# snmp-server host [ip-address] [community-string] [trap-type]

# User and password # username [username] password [password]

# DNS config  # ip name-server [dns-server-ip]

# NTP config  # ntp server [ntp-server-ip]


# snmp_cmd = "snmp-server host {ip-address} {community-string} {trap-type}"


ping_cmd = 'ping {} source {}'
dst_ip = "2.2.2.2"
src_ip= "1.1.1.1"
ping_output = ping_cmd.format(dst_ip, src_ip)
# 'ping 2.2.2.2 source 1.1.1.1'


snmp_cmd = "snmp-server host {} {} {}"
ip = "1.1.1.1"
community_name = "public"
trap_type = "link-down"
snmp_output = snmp_cmd.format(ip, community_name,trap_type )
print(snmp_output)


dns_cmd = "ip name-server {}"
dns_server_ip = "8.8.8.8"
dns_output = dns_cmd.format(dns_server_ip)
print(dns_output)


cmd1 = "username {}  privilege {} password {}"
username = "admin"
priv_level = "15"
password = "netg"
output1 = cmd1.format(username, priv_level, password)
print(output1)



ntp_cmd = "ntp server {}"
ntp_server = "server 0.in.pool.ntp.org"
output2 = ntp_cmd.format(ntp_server)
print(output2)

