# ปัญหาจริงและวิธีแก้ — รุ่น3แหล่ง

1. **OAE/MOCใช้ไม่ทันหรือถูกบล็อก**: ไม่เรียกสองแหล่งนี้อีก เลือกตลาดไทหลังตรวจrobots200และHTMLจริง ไม่เรียกJS/JSONที่robotsห้าม ดึง44รายการที่ตรวจราคา/หน่วย/วันที่สอดคล้องกันได้
2. **ตลาดไทมีราคา2ชุดไม่ตรงกันและข้อมูลเก่า**: ตรวจ67รายการ พบราคาสรุปกับdated snapshotบางรายการขัดแย้งหรือเกิน60วัน ตัด23รายการพร้อมreason ไม่เลือกตัวเลขเอง ไม่ใช้วันscrapeแทนวันที่ราคา
3. **ป้องกันข้อมูลเดิมเสีย**: ใช้Collector DIT/NABCเดิมโดยตรวจASTตรงกัน ไม่มีDDL migration/ลบvolume ตรวจข้อมูลเดิม354แถวครบ13ฟิลด์ยังตรงเดิมหลังเพิ่มแหล่งใหม่
4. **UPSERT/Source outage**: รันDAGสด2รอบสำเร็จ398→398; เมื่อinjectแหล่งที่สามล่ม DIT/NABCยังLoadต่อได้ DBไม่ลดจำนวนแถว เมื่อinjectราคาติดลบ branchปฏิเสธตามคาดและDBยัง398
5. **Dashboardแสดงแหล่งใหม่/เทียบราคาผิดบริบท**: source filterอ่านDBอัตโนมัติ ให้comparisonใช้หน่วย+ประเภท+วันเดียวกัน แยกสีsource ตรวจKPIและกราฟกับSQLจริง ผ่านsource/product/date/empty filter เพิ่มpipeline statusอ่านpipeline_runsจริง
6. **ข้อจำกัดruntimeของสภาพแวดล้อม**: Docker configตรวจได้ แต่daemon socketไม่อนุญาตและnativePostgreSQL16เริ่มเป็นrootไม่ได้ จึงทดสอบเพิ่มเติมด้วยPostgreSQL18.6WASMและSQLiteเฉพาะmetadataของAirflow ไม่อ้างว่าLocalExecutorขนานหรือWindows/Docker16ผ่านในเครื่องนี้

ผลล่าสุดและภาพ: evidence/third_source/; หลักฐาน2แหล่งในevidence/เดิมเก็บเป็นประวัติ ไม่ใช่ผล3แหล่ง
