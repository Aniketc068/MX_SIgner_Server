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


## **🌍 Collaborate & Expand Internationally**
We welcome collaborators and partners who want to help expand MXServerSign globally. If you have suggestions for new features, we'd love to hear from you! 🚀

🔹 Join us in making MXServerSign even better!
💡 Your ideas & feedback can shape the future of secure digital signing.

## 🛠 How to Run the Code  

### **1️⃣ Install Python 3.12 or Above**  
Ensure you have **Python 3.12+** installed on your system. You can download it from:  
🔗 [Python Official Website](https://www.python.org/downloads/)  

### **2️⃣ Create a Virtual Environment**  
Run the following command to create and activate a virtual environment:  

#### **For Windows:**  
```sh
python -m venv signer
signer\Scripts\activate
```

#### **For macOS/Linux:**  
```sh
python3 -m venv signer
source signer/bin/activate
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

### **5️⃣ Access the Web Interface**  
Once the server is running, visit:  

🔗 **[http://127.0.0.1:5020](http://127.0.0.1:5020)**  

🚀 This will open the **MX Server Sign** web interface where you can manage and test digital signing features.  

🎯 **You can now use the APIs to start signing your documents!**  

---

🎯 **Once the server is running, you can use the APIs to start signing your documents!**  

---

## ⚙️ Configuration Settings  

You can **customize various settings** using `env.py`.  

### **🔹 Modify Default Settings (env.py)**  
Edit **`env.py`** to change the following:  
- **Max PDF Size** – Set the maximum PDF size allowed in requests (**`MAX_PDF_SIZE_MB`**)  
- **Default Date Format** – Change the format of dates in signed PDFs (**`Default_Date_Format`**)  
- **Default File Title** – Modify the title of signed PDF files (**`Default_File_Title`**)  
- **Default Signature Coordinates** – Adjust default placement for digital signatures (**`Default_Coordinates`**)  


### **🔹 Change Server IP & Port (managex_signer.config)**  
Edit **`managex_signer.config`** to:  
- **Change the IP & Port** the server runs on  
- Customize other server-related configurations  

---

## 📌 API Endpoints  

### **🔹 Upload PFX File**  
```http
POST http://127.0.0.1:5020/upload
```
**Body (form-data):**  
- `file` (Type: file) – Select the PFX file  
- `pin` (Type: text) – Enter the PIN associated with the PFX file  

### **🔹 Sign a PDF**  
```http
POST http://127.0.0.1:5020/sign/api/v1.0/postjson
```
**Body (raw JSON):**  
```json
{
  "request": {
    "command": "managexserversign", // Mandatory
    "timestamp": "", // Mandatory: Send ISO timestamp
    "transaction_id": "", // Mandatory: Ensure no duplicates
    "pfx": {
      "SN": "" // Mandatory: Uploded Certificate Serial no.
    },
    "pdf": {
      "coordinates": "" // Coordinates for signing
    },
    "pdf_data": "" // Base64 encoded PDF
  }
}
```

---

## 🔒 Security & Compliance  
- Compliant with **legal and regulatory** digital signing standards.  

## 📅 Schedule a Demo  
Discover how **MXServerSign** can simplify and secure your digital signing process.  

👉 **Get Started Today!** 🚀
