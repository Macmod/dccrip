import ipaddress

def IPv4(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError as e:
        return False
