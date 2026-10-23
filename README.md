# Agricultural Prices ETL — 02739452-26-6621655321

นายภาณุพงศ์ อินทะแสน • 6621655321 • หมู่ 820 • ลำดับที่ 26
GitHub: https://github.com/intasan/02739452-26-6621655321

## รุ่น 3 แหล่ง (23 ตุลาคม 2569)

ใช้ ZIP ที่ผู้ใช้แนบเป็นฐาน รักษา Collector DIT/NABC เดิม ไม่ใช้ OAE หรือ MOC ใน DAG อีกต่อไป
แหล่งที่ใช้จริงคือ **DIT + NABC + ตลาดไท (talaadthai)** ไม่มีข้อมูลจำลอง

- DIT82 + NABC274 + ตลาดไท44 =400 แถวก่อน dedup; NABCซ้ำ2แถว จึงเหลือ **398แถว**
- รักษาข้อมูลเดิม354แถวและobservation_keyเดิม ไม่มีการล้างฐานข้อมูลหรือเปลี่ยนหน่วยข้อมูลเดิม
- ผล runtime/UPSERT/outage/Dashboard อยู่ `evidence/third_source/` อ่านเฉพาะไฟล์ผลจริง ไม่อ้างว่าผ่านจากโค้ดอย่างเดียว
- หลักฐานรอบก่อนใน `evidence/` ที่กล่าวถึง354หรือMOCเป็นประวัติ2แหล่ง ไม่ใช่ผลล่าสุดของรุ่นนี้

## แหล่งที่สามที่ตรวจแล้วก่อนเลือก

เลือก `https://talaadthai.com/products` ซึ่งตอบHTTP200และมีราคาจริงในHTMLสาธารณะ
robots.txt ตอบ200: `/products`อนุญาต แต่ห้ามไฟล์`.js`/`.json`บางแบบ จึงใช้requests+BeautifulSoupอ่านเฉพาะHTMLและscript#__NEXT_DATA__ที่ฝังในหน้านั้น ไม่เรียกJS/JSON endpoints ไม่ใช้Selenium
โครงสร้างที่ตรวจจริง: `props.pageProps.productsPriceTrending.data[]` มีid, slug, title.th, unit, priceMinThb/priceMaxThb และ pricingData.latestPriceDiffProductSnapShot.data.current(date,minPrice,maxPrice)

พบ67รายการ แต่รับ44รายการที่ช่วงราคาในdated snapshotตรงกับช่วงราคาสรุป และวันที่อยู่ใน60วันที่ผ่านมา อีก23รายการตัดออกพร้อมเหตุผล ไม่เดาราคา/หน่วย/วันที่ และไม่ติดป้ายว่าทุกรายการเป็นราคาวันนี้
ดูresponseจริงและparser audit: `evidence/third_source/talaadthai-products.json`, `talaadthai-robots.json`, `parse-report.json`, `live-rows.json`
แหล่งทางเลือกที่ตรวจ: ตลาดสี่มุมเมือง `/pricing`ตอบ200แต่HTMLไม่มีแถวราคาในผลตรวจ จึงไม่เลือกและไม่เสียเวลาเจาะระบบป้องกัน

ตลาดไทใช้measurement_type=`wholesale` และmarket_name=`ตลาดไท`; DIT=`retail`, NABC=`market_buying`ตามเดิม จึงไม่รวมราคาข้ามประเภทโดยพลการ
รายละเอียดschema/หน่วย/date/UPSERTอยู่ `COMMON_SCHEMA.md` (ไม่เปลี่ยนDDLเดิม)

## Pipeline และความทนทาน

TaskGroup `parallel_sources`: fetch_dit, fetch_nabc, fetch_talaadthai เป็นtaskอิสระ → merge_and_validate → quality_branch → load_prices / no_valid_data
แต่ละแหล่งคืนok/errorแยกกัน แหล่งหนึ่งล่มยังโหลดแหล่งอื่นได้พร้อมstatus=`partial`; เมื่อไม่มีข้อมูลที่ผ่านหรือพบinvalid rowsจะbranchไปno_valid_dataและfailชัดเจน
Unique observation_key ใช้UPSERT ไม่รวมราคาในkey จึงแก้ราคาวันเดิมได้โดยไม่เพิ่มแถว ใช้keyเดิมของDIT/NABCและไม่dedupคนละตลาด/หน่วย/ประเภท
รายละเอียดsource_status/extracted_rows/error/duplicates/rejectedและinput_modeเก็บในpipeline_runs.details

## Dashboard (รักษาหน้าเดิม)

`web/app.py`อ่านPostgreSQLโดยตรง ไม่มีfallback CSV/sample data
ตัวกรองแหล่งข้อมูลสร้างจากค่าsourceในตาราง จึงเห็นtalaadthaiอัตโนมัติหลังLoad
KPIและtrendเลือกสินค้า+หน่วย+ประเภทเดียว; กราฟเปรียบเทียบใช้หน่วย+ประเภท+วันเดียวกัน แยกแหล่งด้วยสี ไม่เฉลี่ยคนละช่วงเวลาหรือแปลงหน่วยเอง
ถ้ามีแหล่งเดียวในกลุ่มจะแจ้งตามจริง ไม่สร้างแถวมาเติมเพื่อเปรียบเทียบ
เพิ่มexpanderสถานะPipelineล่าสุด อ่านpipeline_runsจริง โดยถ้าอ่านสถานะไม่ได้ยังเปิดตารางราคาได้

## ใช้งานบน Windows / Docker Desktop

แตกZIP เปิดPowerShellในโฟลเดอร์ที่มีdocker-compose.yml เปิดDocker Desktopให้Linux engineพร้อม
**ใช้volumeเดิมได้ ห้าม `docker compose down -v` เพราะจะลบข้อมูลเดิม**

### มีระบบเดิมรันอยู่ (แนะนำ)

```powershell
# คัดลอก dags/, web/, scripts/, COMMON_SCHEMA.md และ README.md รุ่นนี้ทับโฟลเดอร์เดิม
# เก็บ .env เดิมไว้ ไม่ใส่.envลงGitHub
# ตรวจใน.env: AGRI_SOURCES=dit,nabc,talaadthai และ TALAADTHAI_LOOKBACK_DAYS=60
notepad .env
docker compose config --quiet
docker compose restart airflow-scheduler airflow-webserver dashboard
docker compose exec -T airflow-scheduler airflow dags list-import-errors
docker compose exec -T airflow-scheduler airflow dags trigger agri_prices_etl
# รอDAGจบ แล้วตรวจ3แหล่ง
docker compose exec -T airflow-scheduler python /opt/airflow/scripts/db_summary.py
# รันซ้ำ รอจบ และตรวจcount/UPSERT
docker compose exec -T airflow-scheduler airflow dags trigger agri_prices_etl
docker compose exec -T airflow-scheduler python /opt/airflow/scripts/db_summary.py
docker compose exec -T airflow-scheduler python /opt/airflow/scripts/verify_db.py
```

ถ้าแก้.envแล้วต้องการให้ค่าตัวแปรใหม่เข้าcontainer ให้ใช้ `docker compose up -d --force-recreate airflow-scheduler airflow-webserver dashboard` แทนrestart (ไม่ลบvolumePostgreSQL)
ถ้า.envยังมีMOC_KEYWORDSเก่าใช้ไม่ได้แล้ว สามารถลบออก ไม่ต้องสมัครAPIkeyแหล่งที่สาม

### ติดตั้งใหม่

```powershell
powershell -NoProfile -File .\scripts\Run-Windows.ps1
powershell -NoProfile -File .\scripts\Verify-Windows.ps1
```

สคริปต์สร้าง.envและรหัสผ่านสุ่มเมื่อยังไม่มี ไม่เขียนทับรหัสเดิม
Airflow http://localhost:8080 (admin/รหัสใน.env), Dashboard http://localhost:8501
PowerShellและPostgreSQL16บนDockerต้องตรวจผลบนเครื่องWindowsจริง สภาพแวดล้อมทดสอบที่นี่ใช้PostgreSQL18.6WebAssemblyและSQLiteเฉพาะAirflowmetadata ไม่อ้างว่าเป็นDocker16หรือทดสอบLocalExecutorขนานแล้ว

## ตัวเลือกสำรอง 2 แหล่ง

ตั้ง `.env` เป็น `AGRI_SOURCES=dit,nabc` แล้วrecreateเฉพาะAirflow services เพื่อไม่เรียกแหล่งที่สาม ข้อมูลเดิมไม่ถูกลบ
มีZIPสำรอง2แหล่งแยกให้ผู้ใช้ด้วย เวอร์ชันหลักจะส่งเฉพาะเมื่อมีหลักฐาน3แหล่งจริง

## ทดสอบและหลักฐาน

- `tests/test_third_source.py`: parseHTMLจริง44รายการ, schema/unit/date, รักษา354keyเดิมและthird-source outage; รวมtestsเดิมทั้งหมด12กรณี
- `scripts/run_collectors.py`: network extractionจริง3แหล่ง → evidence/collection-three-sources.json
- `scripts/verify_three_sources.py`: liveDAG2รอบ + เทียบข้อมูลเดิม13ฟิลด์ + source outage/invalid-price fault injectionกับสำเนาแถวจริง
- `scripts/dashboard_check.py`: อ่านDBจริง เทียบKPIและกราฟกับSQL ทดสอบsource/product/date/empty filterและPipeline status
- `scripts/verify_db.py`: ใช้แถวจริงในDBทดสอบUPSERTในtransactionแล้วrollback ไม่แทรกข้อมูลตัวอย่าง
- ภาพรอบเก่า2แหล่งและรายงานก่อนหน้าถูกระบุเป็นประวัติ; ผลรอบใหม่อยู่third_source

ไม่เพิ่มforecasting/login/แผนที่ ใช้เฉพาะราคาสาธารณะไม่เก็บข้อมูลผู้ค้า/ผู้ซื้อ ไม่หลบระบบป้องกัน ไม่commit.envหรือAPIkey
