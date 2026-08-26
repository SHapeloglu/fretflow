"""
OMR Debug Script — beam/blob birleşme teşhisi
Kullanım (sunucuda /opt/fretflow/backend içinde, venv aktifken):

    python3 debug_omr.py /tmp/nota.pdf

Çıktı:
  - Konsola: her treble staff için TÜM contour'lar (filtreden geçsin/geçmesin)
    x, y, w, h, area, aspect, cy, hesaplanan step/pitch
  - /tmp/omr_debug/ altına: binary.png, no_staff.png, no_stems.png,
    blobs_overlay.png (her staff için ayrı, staff_0, staff_1, ...)
"""
import sys, os, math
import numpy as np
import cv2
import fitz

sys.path.insert(0, '/opt/fretflow/backend')
from app.services.omr_service import PDFOMRService

TREBLE_MAP = PDFOMRService.TREBLE_MAP

OUT_DIR = '/tmp/omr_debug'
os.makedirs(OUT_DIR, exist_ok=True)


def dump_staff(idx, gray_raw, staff_ys, spacing):
    pad = spacing * 3
    y1 = max(0, min(staff_ys) - pad)
    y2 = min(gray_raw.shape[0], max(staff_ys) + pad)
    x_start = int(gray_raw.shape[1] * 0.15)
    crop = gray_raw[y1:y2, x_start:]

    _, binary = cv2.threshold(crop, 127, 255, cv2.THRESH_BINARY_INV)
    kh = cv2.getStructuringElement(cv2.MORPH_RECT, (spacing * 5, 1))
    no_staff = cv2.subtract(binary, cv2.morphologyEx(binary, cv2.MORPH_OPEN, kh))
    kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, spacing * 2))
    no_stems = cv2.subtract(no_staff, cv2.morphologyEx(no_staff, cv2.MORPH_OPEN, kv))

    cv2.imwrite(f'{OUT_DIR}/staff{idx}_0_crop.png', crop)
    cv2.imwrite(f'{OUT_DIR}/staff{idx}_1_binary.png', binary)
    cv2.imwrite(f'{OUT_DIR}/staff{idx}_2_no_staff.png', no_staff)
    cv2.imwrite(f'{OUT_DIR}/staff{idx}_3_no_stems.png', no_stems)

    staff_local = [y - y1 for y in staff_ys]
    top = min(staff_local) - spacing * 2
    bot = max(staff_local) + spacing * 1.5
    first_line_y = max(staff_local)

    cnts, _ = cv2.findContours(no_stems, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"\n=== STAFF {idx} === staff_ys={staff_ys} spacing={spacing} "
          f"top={top:.1f} bot={bot:.1f} first_line_y={first_line_y}")
    print(f"Toplam contour sayısı: {len(cnts)}")

    overlay = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    rows = []
    for cnt in cnts:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        cx, cy = x + w // 2, y + h // 2
        aspect = w / h if h > 0 else 0
        in_range = top < cy < bot
        passes_area = area > 40 and area < spacing * spacing * 3
        passes_w = w > 8
        passes_h = h > spacing * 0.25 and h < spacing * 2.3
        passes_aspect = 0.5 < aspect < 2.5
        would_pass = in_range and passes_area and passes_w and passes_h and passes_aspect

        step = math.floor((first_line_y - cy) / (spacing / 2))
        step_clamped = max(-4, min(12, step))
        nm, oc, midi = TREBLE_MAP.get(step_clamped, ('C', 4, 60))

        rows.append((x, y, w, h, area, aspect, cy, step, f'{nm}{oc}', would_pass))

        color = (0, 255, 0) if would_pass else (0, 0, 255)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 1)
        cv2.putText(overlay, f'{nm}{oc}', (x, max(y-3,10)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
        if would_pass:
            cv2.circle(overlay, (cx, cy), 2, (255, 0, 0), -1)

    rows.sort(key=lambda r: r[0])  # x'e göre sırala
    print(f"{'x':>5} {'y':>5} {'w':>5} {'h':>5} {'area':>7} {'aspect':>7} "
          f"{'cy':>5} {'step':>5} {'pitch':>6} {'GECER?':>7}")
    for r in rows:
        x, y, w, h, area, aspect, cy, step, pitch, ok = r
        print(f"{x:5d} {y:5d} {w:5d} {h:5d} {area:7.1f} {aspect:7.2f} "
              f"{cy:5d} {step:5d} {pitch:>6} {'EVET' if ok else 'hayir':>7}")

    cv2.imwrite(f'{OUT_DIR}/staff{idx}_4_overlay.png', overlay)

    # Servisin gerçek fonksiyonuyla üretilen final notalar
    svc = PDFOMRService()
    final_notes = svc._detect_notes_in_staff(gray_raw, staff_ys, spacing)
    print(f"\n-- Servisin bulduğu FINAL notalar (staff {idx}) --")
    for n in final_notes:
        print(n)


def main(pdf_path):
    file_bytes = open(pdf_path, 'rb').read()
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(3.0, 3.0), colorspace=fitz.csGRAY)
    img_bytes = pix.tobytes('png')
    doc.close()

    nparr = np.frombuffer(img_bytes, np.uint8)
    gray_raw = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    gray = cv2.GaussianBlur(gray_raw, (3, 3), 0)
    cv2.imwrite(f'{OUT_DIR}/page_full.png', gray_raw)

    svc = PDFOMRService()

    # --- TÜM staff gruplarını (treble+bass, filtrelenmemiş) görmek için
    #     _detect_treble_staffs mantığını burada tekrarlıyoruz ---
    edges = cv2.Canny(gray, 30, 100)
    w = gray.shape[1]
    lines = cv2.HoughLinesP(edges, 1, np.pi/180,
        threshold=int(w*0.5), minLineLength=int(w*0.4), maxLineGap=30)
    h_lines = [l[0] for l in lines if abs(int(l[0][1])-int(l[0][3])) < 4]
    raw_ys = sorted(set(int(l[1]) for l in h_lines))
    groups, group = [], [raw_ys[0]]
    for y in raw_ys[1:]:
        if y - group[-1] <= 8:
            group.append(y)
        else:
            groups.append(int(np.mean(group)))
            group = [y]
    groups.append(int(np.mean(group)))
    print(f"\nToplam çizgi grubu (satır) sayısı: {len(groups)}")
    print(f"Ham gruplar: {groups}")
    all_staffs = [groups[i:i+5] for i in range(0, len(groups), 5) if len(groups[i:i+5]) == 5]
    print(f"5'li staff grubu sayısı (treble+bass toplam): {len(all_staffs)}")
    for i, s in enumerate(all_staffs):
        sp = int(np.mean(np.diff(s))) if len(s) > 1 else 0
        print(f"  ham staff {i}: {s}  spacing~{sp}")

    treble_staffs = svc._detect_treble_staffs(gray)
    print(f"\nBulunan treble staff sayısı: {len(treble_staffs)}")
    for i, s in enumerate(treble_staffs):
        print(f"  staff {i}: {s}")

    for i, staff_ys in enumerate(treble_staffs):
        spacing = int(np.mean(np.diff(staff_ys)))
        dump_staff(i, gray_raw, staff_ys, spacing)

    print(f"\nGörseller şuraya kaydedildi: {OUT_DIR}/")


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/nota.pdf'
    main(path)
