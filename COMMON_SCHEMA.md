# Common Schema (รักษา schema เดิม)

ไม่เพิ่ม/ลบคอลัมน์และไม่เปลี่ยนสูตร observation_key ของ DIT/NABC จึงใช้กับฐานข้อมูลเดิมได้โดยไม่ลบ volume

| ฟิลด์ | DIT | NABC | Talaadthai |
|---|---|---|---|
| source / origin_agency | dit | nabc | talaadthai |
| product_name | ชื่อรวมเกรดจาก HTML | product_name ต้นทาง | title.th เต็ม รวมขนาด/เกรด |
| product_code | รหัส P13... | ค่าตาม adapter เดิม | id สินค้าต้นทาง |
| unit | ค่าเดิม เช่น บาท/กก. | ค่าเดิม เช่น บาท/ตัน | map กิโลกรัม→บาท/กก., กระสอบ→บาท/กระสอบ, ถุง→บาท/ถุง, หวี→บาท/หวี, หน่วยชิ้น/ตัว/หัว/ลูกคงความกำกวมไว้ ไม่แปลงเป็นกิโลกรัม |
| price_min / price_max | ช่วงราคา HTML | day_price สองค่าเท่ากัน | ช่วง current.minPrice/current.maxPrice ต้องตรง priceMinThb/priceMaxThb |
| observed_at | วันที่ พ.ศ. ในตารางแปลง ค.ศ. | data_date | current.date ส่วนวันที่ ไม่ใช้วัน scrape แทน |
| measurement_type | retail | market_buying | wholesale |
| province / market_name | กรุงเทพฯ / ค่าเดิม | จังหวัด/ตลาดต้นทาง | ปทุมธานี / ตลาดไท |
| source_record_id | ค่าเดิม | hash เดิม | id:YYYY-MM-DD |
| source_url | หน้าราคา DIT | URL API พร้อม date | URL สินค้าจริงบน talaadthai.com |

Unique observation_key เดิม = SHA256(origin, ชื่อรวมเกรด, หน่วย, จังหวัด, ตลาด, ประเภท, วันที่) ไม่รวมราคาเพื่อ UPSERT ราคาที่แก้ในวันเดิมได้
ไม่ dedup คนละตลาดหรือคนละประเภท ไม่สร้าง alias รวมสินค้า/แปลงราคาด้วยน้ำหนักที่ไม่มีหลักฐาน
Dashboard เทียบราคาเฉพาะหน่วย+ประเภท+วันเดียวกัน และแยกแหล่งด้วยสี ส่วน trend/KPI เลือกสินค้า+หน่วย+ประเภทหนึ่งกลุ่ม
ข้อมูล snapshot ตลาดไทบางรายการไม่ตรงราคาสรุปหรือเกิน60วันจะถูกตัดพร้อมเหตุผลใน evidence/third_source/parse-report.json ไม่แก้เลขเอง
