'''
Created on 2014/08/20

@author: shimarin
'''
# -*- coding: utf-8 -*-
import os,base64,argparse
import rsa,xattr
import oscar

privatekey_file = os.path.join(oscar.get_oscar_dir(), "etc/private.key")

def parser_setup(parser):
    parser.add_argument("license_string", nargs='?')
    parser.add_argument("signature", nargs='?')
    parser.set_defaults(func=run)

def sign(license_string, privkey):
    return base64.b64encode(rsa.sign(license_string, privkey, "SHA-1"))

def run(args):
    if args.license_string:
        if args.signature:
            if not oscar.verify_license(args.license_string, args.signature):
                raise Exception("Invalid license signature.")
            #else
            oscar.save_license(args.license_string, args.signature)
            print "License saved"
        else:
            if os.path.isfile(privatekey_file):
                privatekey_str = open(privatekey_file).read()
            else:
                privatekey_str = raw_input("Enter private key: ")
            privkey = rsa.PrivateKey.load_pkcs1(base64.b64decode(privatekey_str), "DER")
            license_string = args.license_string.strip()
            print license_string
            print sign(license_string, privkey)
    else:
        print "License string: %s" % oscar.get_license_string()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)
