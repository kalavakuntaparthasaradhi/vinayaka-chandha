import qrcode

upi_link = "upi://pay?pa=6305777042@ybl&pn=Lakshmi%20Ganapathi%20Youth&cu=INR"

qr = qrcode.make(upi_link)

qr.save("static/upi_qr.png")

print("QR code created successfully!")