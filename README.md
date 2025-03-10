# MXServerSign - Secure Digital PDF Signing  

**MXServerSign** by ManageX (India) is a **cloud-based** solution for digitally signing PDFs using **.pfx** files. It ensures **security, compliance, and efficiency**, making document workflows seamless for businesses of all sizes.  

## 🚀 Features  

### ✅ **Core Features:**  
- Secure **.pfx-based** digital PDF signing  
- **Cloud-based** with fast and reliable processing  
- **REST API** for seamless integration  
- **Scalable** for small businesses & enterprises  
- **Compliance** with global digital signing standards  
- **Encryption** ensures document security  

### 🔧 **Advanced API Features:**  
- **Webhook response** for real-time updates  
- **Search by text** to find signing coordinates  
- **Change page number** for signature placement  
- **Add reason, custom text, and location** to signatures  
- **Modify date format** in signature appearance  
- **Enable Apple TSA** for embedding timestamps  
- **Certify PDFs** after signing for extra security  
- **Invisible signatures** for secure verification  
- **Email notifications** after signing  
- **Customize signer’s name** in the signature appearance  
- **Sign PDF from URL** instead of Base64  

---

## 📌 API Endpoints  

### **🔹 Upload PFX File**  
```http
POST https://mxserversign.managexindia.in/upload
```
**Body (form-data):**  
- `file` (Type: file) – Select the PFX file  
- `pin` (Type: text) – Enter the PIN associated with the PFX file  

### **🔹 Sign a PDF**  
```http
POST https://mxserversign.managexindia.in/sign/api/v1.0/postjson
```
**Body (raw JSON):**  
```json
{
  "request": {
    "command": "managexserversign",
    "timestamp": "",
    "transaction_id": "",
    "pfx": {
      "SN": ""
    },
    "pdf": {
      "coordinates": ""
    },
    "pdf_data": ""
  }
}
```

---

## 🔒 Security & Compliance  
- Documents are **encrypted** and can be removed upon request after signing.  
- Compliant with **legal and regulatory** digital signing standards.  

## 📅 Schedule a Demo  
Discover how **MXServerSign** can simplify and secure your digital signing process.  

👉 **Get Started Today!** 🚀
