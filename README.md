# MXServerSign - Secure Digital PDF Signing  

**MXServerSign** by ManageX (India) is a **cloud-based** solution for digitally signing PDFs using **.pfx** files. It ensures **security, compliance, and efficiency**, making document workflows seamless for businesses of all sizes.  

---

## 🚀 Features  

### ✅ **Core Features:**  
- Secure **.pfx-based** digital PDF signing  
- **Cloud-based** with fast and reliable processing  
- **REST API** for seamless integration  
- **Scalable** for small businesses & enterprises  
- **Compliance** with global digital signing standards  

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

## 🛠 How to Run the Code  

### **1️⃣ Install Python 3.12 or Above**  
Ensure you have **Python 3.12+** installed on your system. You can download it from:  
🔗 [Python Official Website](https://www.python.org/downloads/)  

### **2️⃣ Create a Virtual Environment**  
Run the following command to create and activate a virtual environment:  

#### **For Windows:**  
```sh
python -m venv env
env\Scripts\activate
```

#### **For macOS/Linux:**  
```sh
python3 -m venv env
source env/bin/activate
```

### **3️⃣ Install Dependencies**  
Run the following command to install the required dependencies:  
```sh
pip install -r requirements.txt
```

### **4️⃣ Run the Server**  
Now, start the **ManageX Signer Server** by running:  
```sh
python ManageX_Signer_Server.py
```

🎯 **Once the server is running, you can use the APIs to start signing your documents!**  

---

## ⚙️ Configuration Settings  

You can **customize various settings** using `env.py` and `managex_signer.config`.  

### **🔹 Modify SMTP Email Settings & Other Defaults (env.py)**  
Edit **`env.py`** to change the following:  
- **SMTP Settings** – Update email server settings  
- **TSA URL** – Change the Timestamp Authority (TSA) URL  
- **Max PDF Size** – Set the maximum PDF size allowed in requests  
- **Default Date Format** – Change the format of dates in signed PDFs  
- **Default File Title** – Modify the title of signed PDF files  
- **Default Signature Coordinates** – Adjust default placement for digital signatures  
- **Temp Mail Blocking** – Modify `temp-mail.config` to block specific domains from receiving emails  

### **🔹 Change Server IP & Port (managex_signer.config)**  
Edit **`managex_signer.config`** to:  
- **Change the IP & Port** the server runs on  
- Customize other server-related configurations  

---

## 📌 API Endpoints  

### **🔹 Upload PFX File**  
```http
POST http://127.0.0.1/upload
```
**Body (form-data):**  
- `file` (Type: file) – Select the PFX file  
- `pin` (Type: text) – Enter the PIN associated with the PFX file  

### **🔹 Sign a PDF**  
```http
POST http://127.0.0.1/sign/api/v1.0/postjson
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
- Compliant with **legal and regulatory** digital signing standards.  

## 📅 Schedule a Demo  
Discover how **MXServerSign** can simplify and secure your digital signing process.  

👉 **Get Started Today!** 🚀
