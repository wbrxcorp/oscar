import oscar,web

if __name__ == "__main__":
    oscar.init()
    try:
        web.app.run(host='0.0.0.0',debug=True)
    finally:
        oscar.fin()
