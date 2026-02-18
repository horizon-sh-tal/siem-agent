# FTP Access Testing Commands

## From Prof-1, Prof-2, Dev-1, Dev-2

1. Open terminal or command prompt.
2. Connect to FTP server:
   ```
   ftp [FTP_SERVER_IP]
   ```
3. Login as guest, prof1, or prof2 (use correct password).
4. List directories:
   ```
   ls
   cd prof1
   ls
   cd MoUs
   ls
   cd ..
   cd research
   ls
   cd ..
   cd datasets
   ls
   ```
5. Test upload/download:
   ```
   put testfile.txt
   get README.txt
   ```
6. Exit:
   ```
   bye
   ```

---
Replace [FTP_SERVER_IP] with the actual IP of your FTP server VM.
