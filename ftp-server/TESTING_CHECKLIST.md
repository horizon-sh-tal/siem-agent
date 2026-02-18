# FTP Server Testing Checklist

Complete this checklist to verify your FTP honeypot is working correctly.

---

## Pre-Deployment Tests (on FTP Server VM)

### ✅ Step 1: Verify Files Are Present
```bash
cd ~/ftp-server
ls -la

# Should see:
# - docker-compose.yml
# - add_ftp_users.sh
# - ftp_monitor.py
# - generate_fake_assets.sh
# - deploy_ftp.sh
```
- [ ] All files present

### ✅ Step 2: Check Docker Installation
```bash
docker --version
docker-compose --version

# Should show versions
```
- [ ] Docker installed
- [ ] Docker Compose installed

### ✅ Step 3: Verify Fake Assets Generated
```bash
cd ~/ftp-server
find ftp-data -type f | wc -l

# Should show ~80+ files
```
- [ ] ftp-data/ directory exists
- [ ] prof1/ has MoUs, research, datasets
- [ ] prof2/ has MoUs, research, datasets
- [ ] guest/ has README
- [ ] Total ~80 files

### ✅ Step 4: Check Containers Running
```bash
docker ps

# Should show:
# - ftp-server (running)
# - ftp-monitor (running)
```
- [ ] ftp-server container running
- [ ] ftp-monitor container running

### ✅ Step 5: Verify FTP Port Listening
```bash
netstat -tuln | grep 21

# Should show: tcp 0.0.0.0:21 LISTEN
```
- [ ] Port 21 is listening

---

## Local Tests (on FTP Server VM)

### ✅ Test 1: Guest Account
```bash
ftp localhost
# Username: guest
# Password: guest123
ftp> ls
ftp> get README.txt
ftp> bye
```
- [ ] Can login as guest
- [ ] Can list files
- [ ] Can download README.txt

### ✅ Test 2: Prof1 Account
```bash
ftp localhost
# Username: prof1
# Password: Maharanapratap!
ftp> ls
ftp> cd MoUs
ftp> ls
ftp> cd ../research
ftp> ls
ftp> cd ../datasets
ftp> ls
ftp> bye
```
- [ ] Can login as prof1
- [ ] MoUs directory accessible
- [ ] research directory accessible
- [ ] datasets directory accessible
- [ ] Can see PDF and CSV files

### ✅ Test 3: Prof2 Account
```bash
ftp localhost
# Username: prof2
# Password: gogreen@7560
ftp> ls
ftp> cd MoUs
ftp> ls
ftp> bye
```
- [ ] Can login as prof2
- [ ] Can access prof2 directories

### ✅ Test 4: Monitor Logs
```bash
docker logs ftp-monitor --tail 20

# Should show:
# - "FTP Activity Monitor Starting"
# - "Connected to Kafka broker"
# - "Initial scan complete: XX files found"
```
- [ ] Monitor connected to Kafka
- [ ] Initial scan completed
- [ ] No errors in logs

---

## Remote Tests (from Prof/Dev VMs)

### ✅ Test 5: Access from Prof-1 (192.168.27.212)

**On Windows PowerShell:**
```powershell
ftp 192.168.27.211
# Username: prof1
# Password: Maharanapratap!
ftp> dir
ftp> cd MoUs
ftp> dir
ftp> get MoU_Health_and_Family_Welfare_2024.pdf
ftp> bye
```

**On Linux:**
```bash
ftp 192.168.27.211
# Same as above
```

- [ ] Can connect from Prof-1
- [ ] Can login as prof1
- [ ] Can list directories
- [ ] Can download PDF file

### ✅ Test 6: Access from Prof-2 (192.168.27.155)
```bash
ftp 192.168.27.211
# Username: prof2
# Password: gogreen@7560
ftp> ls
ftp> cd research
ftp> ls
ftp> bye
```
- [ ] Can connect from Prof-2
- [ ] Can login as prof2
- [ ] Can access research directory

### ✅ Test 7: Access from Dev-1 (192.168.27.200)
```bash
ftp 192.168.27.211
# Username: guest
# Password: guest123
ftp> ls
ftp> get README.txt
ftp> bye
```
- [ ] Can connect from Dev-1
- [ ] Can login as guest
- [ ] Can download files

### ✅ Test 8: Access from Dev-2 (192.168.27.54)
```bash
ftp 192.168.27.211
# Username: guest
# Password: guest123
ftp> ls
ftp> bye
```
- [ ] Can connect from Dev-2
- [ ] Guest account works

---

## Monitoring Tests

### ✅ Test 9: Upload File (Trigger Activity)
```bash
# From any VM
ftp 192.168.27.211
# Login as prof1
ftp> cd MoUs
ftp> put test_upload.txt
ftp> ls
ftp> bye
```
- [ ] File upload successful
- [ ] File visible in directory

### ✅ Test 10: Check Monitor Detected Upload
```bash
# On FTP Server VM
docker logs ftp-monitor --tail 50

# Wait up to 30 minutes for next scan
# Should see:
# - "New file detected: prof1/MoUs/test_upload.txt"
# - "Sent activity log to Kafka"
```
- [ ] Monitor detected new file
- [ ] Log sent to Kafka

### ✅ Test 11: Verify Kafka Received Message
```bash
# On Kafka VM (192.168.27.211)
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic ftp-activity-logs \
    --from-beginning

# Should show JSON message with:
# - "new_files": [{"filename": "test_upload.txt", ...}]
```
- [ ] Kafka received message
- [ ] Message contains file details

### ✅ Test 12: Modify File (Trigger Hash Change)
```bash
# From any VM
ftp 192.168.27.211
# Login as prof1
ftp> cd MoUs
ftp> put test_upload.txt  # Upload again with different content
ftp> bye

# Wait 30 min, check logs:
docker logs ftp-monitor --tail 50
# Should see: "Modified file detected"
```
- [ ] Modified file detected
- [ ] Hash change recorded

### ✅ Test 13: Delete File
```bash
ftp 192.168.27.211
# Login as prof1
ftp> cd MoUs
ftp> delete test_upload.txt
ftp> bye

# Wait 30 min, check logs
# Should see: "Deleted file detected"
```
- [ ] Deleted file detected
- [ ] Deletion logged to Kafka

---

## Security Tests

### ✅ Test 14: Firewall Rules
```bash
# On FTP Server VM
sudo ufw status

# Should show:
# - 21/tcp from 192.168.27.0/24
# - 30000:30009/tcp from 192.168.27.0/24
```
- [ ] Firewall enabled
- [ ] FTP ports restricted to internal network

### ✅ Test 15: Invalid Login Attempt
```bash
ftp 192.168.27.211
# Username: hacker
# Password: wrongpass

# Should fail
```
- [ ] Invalid login rejected
- [ ] No access granted

### ✅ Test 16: Guest Cannot Access Prof Directories
```bash
ftp 192.168.27.211
# Username: guest
# Password: guest123
ftp> cd /home/ftpusers/prof1
# Should fail: Permission denied
```
- [ ] Guest cannot access prof1
- [ ] Permission denied

---

## Performance Tests

### ✅ Test 17: Large File Transfer
```bash
# Create 10MB test file
dd if=/dev/zero of=test_10mb.bin bs=1M count=10

ftp 192.168.27.211
# Login as prof1
ftp> binary
ftp> put test_10mb.bin
ftp> bye
```
- [ ] Large file uploads successfully
- [ ] Transfer completes without errors

### ✅ Test 18: Multiple Concurrent Connections
```bash
# Open 3 terminals and connect simultaneously
# Terminal 1:
ftp 192.168.27.211  # Login as guest

# Terminal 2:
ftp 192.168.27.211  # Login as prof1

# Terminal 3:
ftp 192.168.27.211  # Login as prof2

# All should work
```
- [ ] Multiple connections allowed
- [ ] No connection refused errors

---

## Integration Tests

### ✅ Test 19: Container Restart Resilience
```bash
# On FTP Server VM
docker-compose restart ftp

# Wait 30 seconds
docker ps | grep ftp-server
# Should show running

# Test FTP access
ftp localhost
# Should work
```
- [ ] Container restarts successfully
- [ ] FTP still accessible after restart
- [ ] No data loss

### ✅ Test 20: Monitor Restart Resilience
```bash
docker-compose restart ftp-monitor

docker logs ftp-monitor --tail 20
# Should reconnect to Kafka
```
- [ ] Monitor restarts successfully
- [ ] Reconnects to Kafka
- [ ] Resumes monitoring

### ✅ Test 21: Full System Restart
```bash
# Reboot FTP Server VM
sudo reboot

# After reboot:
docker ps
# Containers should auto-start (restart: always)
```
- [ ] Containers start on boot
- [ ] FTP accessible after reboot
- [ ] Monitor reconnects to Kafka

---

## Data Integrity Tests

### ✅ Test 22: File Hash Verification
```bash
# Upload a file
echo "Test content" > test.txt
ftp 192.168.27.211
# Upload test.txt as prof1

# Check monitor logs for hash
docker logs ftp-monitor | grep test.txt
# Should show SHA256 hash
```
- [ ] Hash calculated for uploaded file
- [ ] Hash logged correctly

### ✅ Test 23: Verify All Fake Assets Present
```bash
cd ~/ftp-server
find ftp-data/prof1/MoUs -name "*.pdf" | wc -l
# Should be 7

find ftp-data/prof1/research -name "*.pdf" | wc -l
# Should be 12

find ftp-data/prof1/datasets -name "*.csv" | wc -l
# Should be 5
```
- [ ] 7 MoU PDFs in prof1
- [ ] 12 research PDFs in prof1
- [ ] 5 CSV datasets in prof1
- [ ] Same for prof2

---

## Final Checklist

### Infrastructure
- [ ] Ubuntu 20.04 Server VM running
- [ ] Docker and Docker Compose installed
- [ ] All required tools installed (enscript, ghostscript)
- [ ] Network connectivity to Prof/Dev VMs
- [ ] Firewall configured correctly

### FTP Server
- [ ] FTP server container running
- [ ] Port 21 listening
- [ ] Passive ports 30000-30009 open
- [ ] 3 accounts working (guest, prof1, prof2)
- [ ] All fake assets accessible

### Monitoring
- [ ] ftp-monitor container running
- [ ] Connected to Kafka (192.168.27.211:9092)
- [ ] Initial scan completed
- [ ] 30-minute scan cycle working
- [ ] Activity logs sent to Kafka

### Testing
- [ ] Local FTP access works
- [ ] Remote access from all 4 VMs works
- [ ] File upload/download works
- [ ] Activity monitoring works
- [ ] Kafka receives messages

### Security
- [ ] Firewall restricts access to internal network
- [ ] Invalid logins rejected
- [ ] Guest cannot access prof directories
- [ ] All traffic logged

### Documentation
- [ ] README.md reviewed
- [ ] INSTALLATION_GUIDE.md available
- [ ] All scripts have executable permissions

---

## Troubleshooting Reference

If any test fails, refer to:
1. `INSTALLATION_GUIDE.md` - Troubleshooting section
2. Docker logs: `docker-compose logs -f`
3. Monitor logs: `docker logs ftp-monitor -f`
4. FTP logs: `docker logs ftp-server -f`

---

## Success Criteria

✅ **All tests passed** = FTP honeypot is ready for production deployment

If 95%+ tests pass, the system is considered functional. Minor issues can be addressed as needed.

---

## Next Steps After Testing

1. ✅ Document any issues encountered
2. ✅ Save test results
3. ⏭️ Integrate with main ADAPT honeypot network
4. ⏭️ Deploy Chatterbox on all VMs
5. ⏭️ Begin 100-day monitoring period
6. ⏭️ Set up Elasticsearch/Kibana for visualization

---

**Testing Date**: __________  
**Tester**: __________  
**Results**: _____ / 23 tests passed  
**Status**: ☐ Pass ☐ Fail ☐ Partial Pass

**Notes**:
