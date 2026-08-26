"""
OMR Service — Smart TAB Engine (Hibrit Pipeline)

Giriş formatları ve pipeline:
  MusicXML (.xml, .musicxml) → music21 parse  ← en doğru
  MIDI     (.mid, .midi)     → music21 parse  ← tempo + nota
  PNG/JPG  (.png, .jpg)      → opencv OMR     ← basit notalar
  PDF      (.pdf)            → görüntüye çevir + opencv OMR

Katman 1 (Notadan Okunan): Pitch, Duration, Tempo, Time Signature
Katman 2 (Sistem Üretilen): Fingering, String, Ritim ↓↑
"""
import hashlib
import math
import re
import io
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import cv2

# ── Müzik sabitleri ──────────────────────────────────────────────
MIDI_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

TREBLE_MAP = {
    -4:('A',3,57), -3:('B',3,59), -2:('C',4,60), -1:('D',4,62),
     0:('E',4,64),  1:('F',4,65),  2:('G',4,67),  3:('A',4,69),
     4:('B',4,71),  5:('C',5,72),  6:('D',5,74),  7:('E',5,76),
     8:('F',5,77),  9:('G',5,79), 10:('A',5,81), 11:('B',5,83),
    12:('C',6,84),
}


class OMRService:
    """
    Hibrit OMR servisi.
    Giriş formatına göre en uygun pipeline'ı otomatik seçer.
    """

    def process_file(self, file_bytes: bytes, filename: str) -> dict:
        """
        Ana giriş noktası. Dosya uzantısına göre doğru parser'ı çağırır.
        """
        ext = Path(filename).suffix.lower()

        if ext in ('.xml', '.musicxml', '.mxl'):
            return self._parse_musicxml(file_bytes)
        elif ext in ('.mid', '.midi'):
            return self._parse_midi(file_bytes)
        elif ext == '.pdf':
            return self._parse_pdf(file_bytes)
        elif ext in ('.png', '.jpg', '.jpeg', '.webp'):
            return self._parse_image(file_bytes)
        else:
            return self._fallback()

    # ── MusicXML Parser (en doğru yol) ───────────────────────────

    def _parse_musicxml(self, file_bytes: bytes) -> dict:
        """
        music21 ile MusicXML parse eder.
        Pitch, duration, tempo, time signature, key hepsini okur.
        """
        try:
            from music21 import converter, tempo as m21tempo, meter, key as m21key

            with tempfile.NamedTemporaryFile(suffix='.musicxml', delete=False) as f:
                f.write(file_bytes)
                tmp_path = f.name

            score = converter.parse(tmp_path)
            os.unlink(tmp_path)

            # Tempo
            tempo_val = 120
            tempos = score.flatten().getElementsByClass(m21tempo.MetronomeMark)
            if tempos:
                t = list(tempos)[0]
                if t.number:
                    tempo_val = int(t.number)

            # Time signature
            time_sig = '4/4'
            meters = score.flatten().getElementsByClass(meter.TimeSignature)
            if meters:
                ts = list(meters)[0]
                time_sig = f'{ts.numerator}/{ts.denominator}'

            # Notalar (sadece treble clef / ilk part)
            notes = []
            target_part = score.parts[0] if score.parts else score
            beat = 1.0
            beats_per_measure = int(time_sig.split('/')[0])

            for element in target_part.flatten().notes:
                # Tekli nota
                if hasattr(element, 'pitch'):
                    pitch = str(element.pitch.name) + str(element.pitch.octave)
                    midi = element.pitch.midi
                    dur = float(element.duration.quarterLength)
                    offset = float(element.offset)
                    beat = (offset % (beats_per_measure)) + 1.0

                    notes.append({
                        'pitch': pitch,
                        'midi': midi,
                        'duration': dur,
                        'beat': round(beat, 2),
                    })
                # Akor - en yüksek notayı al (melodi)
                elif hasattr(element, 'pitches') and element.pitches:
                    top = max(element.pitches, key=lambda p: p.midi)
                    pitch = str(top.name) + str(top.octave)
                    midi = top.midi
                    dur = float(element.duration.quarterLength)
                    offset = float(element.offset)
                    beat = (offset % beats_per_measure) + 1.0

                    notes.append({
                        'pitch': pitch,
                        'midi': midi,
                        'duration': dur,
                        'beat': round(beat, 2),
                    })

            omr_data = {
                'tempo': tempo_val,
                'time_signature': time_sig,
                'key': 'C',
                'notes': notes,
                'source': 'musicxml',
            }
            return {'music_hash': self._hash(omr_data), 'omr_data': omr_data}

        except Exception as e:
            print(f'MusicXML parse hatası: {e}')
            return self._fallback()

    # ── MIDI Parser ───────────────────────────────────────────────

    def _parse_midi(self, file_bytes: bytes) -> dict:
        """
        music21 ile MIDI parse eder.
        Tempo ve nota sürelerini doğru okur.
        """
        try:
            from music21 import converter, tempo as m21tempo, meter

            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
                f.write(file_bytes)
                tmp_path = f.name

            score = converter.parse(tmp_path)
            os.unlink(tmp_path)

            # Tempo
            tempo_val = 120
            tempos = score.flatten().getElementsByClass(m21tempo.MetronomeMark)
            if tempos:
                t = list(tempos)[0]
                if t.number:
                    tempo_val = int(t.number)

            # Time signature
            time_sig = '4/4'
            meters = score.flatten().getElementsByClass(meter.TimeSignature)
            if meters:
                ts = list(meters)[0]
                time_sig = f'{ts.numerator}/{ts.denominator}'

            notes = []
            beats_per_measure = int(time_sig.split('/')[0])
            target_part = score.parts[0] if score.parts else score

            for element in target_part.flatten().notes:
                if hasattr(element, 'pitch'):
                    pitch = str(element.pitch.name) + str(element.pitch.octave)
                    midi = element.pitch.midi
                    dur = float(element.duration.quarterLength)
                    offset = float(element.offset)
                    beat = (offset % beats_per_measure) + 1.0
                    notes.append({
                        'pitch': pitch, 'midi': midi,
                        'duration': dur, 'beat': round(beat, 2),
                    })
                elif hasattr(element, 'pitches') and element.pitches:
                    top = max(element.pitches, key=lambda p: p.midi)
                    pitch = str(top.name) + str(top.octave)
                    notes.append({
                        'pitch': pitch, 'midi': top.midi,
                        'duration': float(element.duration.quarterLength),
                        'beat': round((float(element.offset) % beats_per_measure) + 1.0, 2),
                    })

            omr_data = {
                'tempo': tempo_val, 'time_signature': time_sig,
                'key': 'C', 'notes': notes, 'source': 'midi',
            }
            return {'music_hash': self._hash(omr_data), 'omr_data': omr_data}

        except Exception as e:
            print(f'MIDI parse hatası: {e}')
            return self._fallback()

    # ── PDF Parser ────────────────────────────────────────────────

    def _parse_pdf(self, file_bytes: bytes) -> dict:
        """
        PDF için gelişmiş multi-staff OMR pipeline.
        PyMuPDF ile 3x zoom, tüm treble staffları okur.
        """
        try:
            pdf_svc = PDFOMRService()
            result = pdf_svc.process_pdf(file_bytes)
            if result and result['omr_data']['notes']:
                return result
        except Exception as e:
            print(f'PDF OMR hatası: {e}')
        return self._fallback()

    # ── Image / OpenCV OMR Parser ─────────────────────────────────

    def _parse_image(self, image_bytes: bytes) -> dict:
        """
        PNG/JPG için opencv tabanlı OMR pipeline.
        Basit tek sistem notalar için çalışır.
        """
        try:
            import pytesseract
            nparr = np.frombuffer(image_bytes, np.uint8)
            gray_raw = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if gray_raw is None:
                return self._fallback()

            h, w = gray_raw.shape
            if w < 400:
                scale = 400 / w
                gray_raw = cv2.resize(gray_raw, (int(w*scale), int(h*scale)),
                                      interpolation=cv2.INTER_CUBIC)

            gray = cv2.GaussianBlur(gray_raw, (3, 3), 0)

            # Çok satırlı sistemlerde ilk treble staff'ı al
            staff_ys, spacing = self._detect_staff_lines(gray)
            if not staff_ys:
                return self._fallback()

            binary = self._binarize(gray)
            no_stems = self._remove_staff_and_stems(binary, staff_ys, spacing)
            note_heads = self._detect_note_heads(no_stems, staff_ys, spacing)
            tempo = self._detect_tempo(gray_raw, staff_top=min(staff_ys))
            time_sig = self._detect_time_signature(gray_raw, staff_ys)

            omr_data = self._build_music_data(
                note_heads, staff_ys, spacing, tempo, time_sig
            )
            omr_data['source'] = 'opencv_omr'
            return {'music_hash': self._hash(omr_data), 'omr_data': omr_data}

        except Exception as e:
            print(f'Image OMR hatası: {e}')
            return self._fallback()

    # ── OpenCV pipeline metodları ─────────────────────────────────

    def _detect_staff_lines(self, gray):
        edges = cv2.Canny(gray, 30, 100)
        w = gray.shape[1]
        lines = cv2.HoughLinesP(
            edges, 1, np.pi/180,
            threshold=int(w*0.35),
            minLineLength=int(w*0.25),
            maxLineGap=25,
        )
        if lines is None:
            return [], 15

        h_lines = [l[0] for l in lines if abs(int(l[0][1])-int(l[0][3])) < 4]
        if len(h_lines) < 5:
            return [], 15

        raw_ys = sorted(set(int(l[1]) for l in h_lines))
        groups, group = [], [raw_ys[0]]
        for y in raw_ys[1:]:
            if y - group[-1] <= 5:
                group.append(y)
            else:
                groups.append(int(np.mean(group)))
                group = [y]
        groups.append(int(np.mean(group)))
        groups = sorted(groups)

        if len(groups) < 5:
            return [], 15

        staff = groups[:5]
        spacing = int(np.median(np.diff(staff)))
        return staff, max(spacing, 8)

    def _binarize(self, gray):
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        return binary

    def _remove_staff_and_stems(self, binary, staff_ys, spacing):
        kh = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, spacing*3), 1))
        no_staff = cv2.subtract(binary, cv2.morphologyEx(binary, cv2.MORPH_OPEN, kh))
        kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, spacing*2))
        return cv2.subtract(no_staff, cv2.morphologyEx(no_staff, cv2.MORPH_OPEN, kv))

    def _detect_note_heads(self, no_stems, staff_ys, spacing):
        top = min(staff_ys) - spacing*3
        bot = max(staff_ys) + spacing*2

        def find_blobs(min_h_ratio):
            cnts, _ = cv2.findContours(no_stems, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
            notes = []
            for cnt in cnts:
                x, y, w, h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                cx, cy = x+w//2, y+h//2
                aspect = w/h if h > 0 else 0
                if (area > 15 and top < cy < bot and w > 5
                        and h > spacing*min_h_ratio and 0.6 < aspect < 5.5):
                    notes.append({'cx': cx, 'cy': cy})
            notes.sort(key=lambda n: n['cx'])
            merged, px = [], -999
            for n in notes:
                if n['cx'] - px >= spacing * 0.7:
                    merged.append(n)
                    px = n['cx']
            return merged

        primary = find_blobs(0.5)
        secondary = find_blobs(0.25)
        for n in secondary:
            if not any(abs(n['cx']-p['cx']) < spacing for p in primary):
                primary.append(n)
        primary.sort(key=lambda n: n['cx'])
        return primary

    def _y_to_pitch(self, cy, staff_ys, spacing):
        first_line_y = max(staff_ys)
        step = math.floor((first_line_y - cy) / (spacing / 2))
        step = max(-4, min(12, step))
        if step in TREBLE_MAP:
            name, octave, midi = TREBLE_MAP[step]
            return f'{name}{octave}', midi
        return 'C4', 60

    def _detect_tempo(self, gray_raw, staff_top=80) -> int:
        try:
            import pytesseract
            region = gray_raw[:max(staff_top, 20), :]
            if region.shape[0] < 5:
                return 120
            big = cv2.resize(region, (region.shape[1]*3, region.shape[0]*3),
                             interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(big, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh, config='--psm 6')
            numbers = re.findall(r'\d{2,3}', text)
            valid = [int(n) for n in numbers if 40 <= int(n) <= 240]
            return valid[0] if valid else 120
        except Exception:
            return 120

    def _detect_time_signature(self, gray_raw, staff_ys) -> str:
        try:
            if not staff_ys:
                return '4/4'
            import pytesseract
            top = min(staff_ys) - 5
            bot = max(staff_ys) + 5
            left = gray_raw[max(0,top):bot, :58]
            if left.shape[0] < 5 or left.shape[1] < 5:
                return '4/4'
            big = cv2.resize(left, (left.shape[1]*6, left.shape[0]*3),
                             interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(big, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(
                thresh,
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'
            )
            digits = re.findall(r'\d', text)
            if len(digits) >= 2:
                num, den = int(digits[0]), int(digits[1])
                if 2 <= num <= 12 and den in (2, 4, 8, 16):
                    return f'{num}/{den}'
        except Exception:
            pass
        return '4/4'

    def _build_music_data(self, note_heads, staff_ys, spacing,
                          tempo, time_sig) -> dict:
        beats_per_measure = int(time_sig.split('/')[0])
        notes, beat = [], 1.0
        for n in note_heads:
            pitch, midi = self._y_to_pitch(n['cy'], staff_ys, spacing)
            if beat > beats_per_measure:
                beat = 1.0
            notes.append({
                'pitch': pitch, 'midi': midi,
                'duration': 1.0, 'beat': round(beat, 2),
            })
            beat += 1.0
        return {'tempo': tempo, 'time_signature': time_sig,
                'key': 'C', 'notes': notes}

    # ── Ortak yardımcılar ─────────────────────────────────────────

    def _fallback(self) -> dict:
        omr_data = {
            'tempo': 120, 'time_signature': '4/4', 'key': 'C',
            'source': 'fallback',
            'notes': [
                {'pitch':'E4','midi':64,'duration':1.0,'beat':1.0},
                {'pitch':'F4','midi':65,'duration':1.0,'beat':2.0},
                {'pitch':'G4','midi':67,'duration':1.0,'beat':3.0},
                {'pitch':'E4','midi':64,'duration':1.0,'beat':4.0},
            ],
        }
        return {'music_hash': self._hash(omr_data), 'omr_data': omr_data}

    def _hash(self, omr_data: dict) -> str:
        seq = [f"{n['pitch']}-{n['duration']}" for n in omr_data.get('notes', [])]
        content = (f"{omr_data.get('tempo')}-"
                   f"{omr_data.get('time_signature')}-"
                   f"{'|'.join(seq)}")
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # ── Geriye dönük uyumluluk ────────────────────────────────────

    def process_image(self, image_bytes: bytes) -> dict:
        """Eski PNG-only API ile uyumluluk için."""
        return self._parse_image(image_bytes)


# ── Guitar Mapping ────────────────────────────────────────────────

class GuitarMappingService:
    """Katman 2: Sistem Üretilen — fingering, string, ritim ↓↑"""
    STRING_OPEN_MIDI = [64, 59, 55, 50, 45, 40]  # e B G D A E

    def map_notes_to_tab(self, omr_data: dict) -> dict:
        notes = omr_data.get('notes', [])
        tempo = omr_data.get('tempo', 120)
        time_sig = omr_data.get('time_signature', '4/4')
        tab_notes, prev = [], None

        for note in notes:
            midi = note.get('midi') or self._pitch_to_midi(note['pitch'])
            m = self._best_pos(midi, prev)
            tab_notes.append({
                'beat': note['beat'],
                'pitch': note['pitch'],
                'duration': note['duration'],
                'string': m['string'],
                'fret': m['fret'],
                'finger': m['finger'],
                'rhythm': self._rhythm(note, time_sig),
                'source': note.get('source', 'system'),
            })
            prev = m

        return {'tempo': tempo, 'time_signature': time_sig, 'notes': tab_notes}

    def _best_pos(self, midi, prev):
        candidates = []
        for i, open_midi in enumerate(self.STRING_OPEN_MIDI):
            fret = midi - open_midi
            if 0 <= fret <= 12:
                cost = (abs(fret - (prev['fret'] if prev else 0))
                        + abs(i - (prev['string']-1 if prev else 2)) * 0.5)
                candidates.append({
                    'string': i+1, 'fret': fret,
                    'finger': self._finger(fret, prev), 'cost': cost,
                })
        return (min(candidates, key=lambda c: c['cost'])
                if candidates else {'string':1,'fret':0,'finger':0})

    def _finger(self, fret, prev):
        if fret == 0:
            return 0
        if prev and prev['fret'] > 0:
            return max(1, min(4, prev.get('finger', 1) + fret - prev['fret']))
        return min(4, max(1, fret))

    def _rhythm(self, note, time_sig):
        beat = note.get('beat', 1)
        beats = int(time_sig.split('/')[0])
        return '↓' if (beat in {1, beats//2+1} or beat == int(beat)) else '↑'

    def _pitch_to_midi(self, pitch):
        names = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,
                 'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
        try:
            note = pitch[:-1]
            octave = int(pitch[-1])
            return (octave + 1) * 12 + names.get(note, 0)
        except Exception:
            return 60


# ── Trust Score ───────────────────────────────────────────────────

class TrustScoreService:
    LEVEL_WEIGHTS = {'beginner': 1.0, 'intermediate': 1.5, 'advanced': 3.0}

    def compute_trust_score(self, accuracy: float, rate: float) -> float:
        return round(accuracy * 0.7 + rate * 0.3, 3)

    def get_level_weight(self, level: str) -> float:
        return self.LEVEL_WEIGHTS.get(level, 1.0)

    def classify_tab(self, tab) -> str:
        if tab.accuracy_count >= 5:
            return 'verified'
        if tab.rate_score >= 4.0 and tab.vote_count >= 3:
            return 'high_rated'
        return 'new'



class PDFOMRService:
    """
    PDF için geliştirilmiş OMR — PyMuPDF + multi-staff detection.
    Tek sistem yerine tüm treble staffları okur.
    """

    TREBLE_MAP = {
        -4:('A',3,57),-3:('B',3,59),-2:('C',4,60),-1:('D',4,62),
         0:('E',4,64), 1:('F',4,65), 2:('G',4,67), 3:('A',4,69),
         4:('B',4,71), 5:('C',5,72), 6:('D',5,74), 7:('E',5,76),
         8:('F',5,77), 9:('G',5,79),10:('A',5,81),11:('B',5,83),
        12:('C',6,84),
    }

    def process_pdf(self, file_bytes: bytes) -> dict:
        import fitz, hashlib
        try:
            doc = fitz.open(stream=file_bytes, filetype='pdf')
            pix = doc[0].get_pixmap(
                matrix=fitz.Matrix(3.0, 3.0),
                colorspace=fitz.csGRAY
            )
            img_bytes = pix.tobytes('png')
            doc.close()

            import numpy as np
            nparr = np.frombuffer(img_bytes, np.uint8)
            gray_raw = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            gray = cv2.GaussianBlur(gray_raw, (3,3), 0)

            tempo = self._detect_tempo_pdf(gray_raw)
            time_sig = self._detect_time_sig_pdf(gray_raw)
            treble_staffs = self._detect_treble_staffs(gray)
            
            all_notes = []
            beat = 1.0
            beats_per_measure = int(time_sig.split('/')[0])

            for staff_ys in treble_staffs:
                spacing = int(np.mean(np.diff(staff_ys)))
                notes = self._detect_notes_in_staff(gray_raw, staff_ys, spacing)
                for n in notes:
                    if beat > beats_per_measure:
                        beat = 1.0
                    all_notes.append({
                        'pitch': n['pitch'],
                        'midi': n['midi'],
                        'duration': 1.0,
                        'beat': round(beat, 2),
                    })
                    beat += 1.0

            omr_data = {
                'tempo': tempo,
                'time_signature': time_sig,
                'key': 'C',
                'notes': all_notes,
                'source': 'pdf_omr',
            }
            music_hash = hashlib.sha256(
                '|'.join(f"{n['pitch']}" for n in all_notes).encode()
            ).hexdigest()[:16]
            return {'music_hash': music_hash, 'omr_data': omr_data}

        except Exception as e:
            print(f'PDF OMR hatası: {e}')
            return None
    
    def _group_staff_lines(self, groups):
        staves = []
        current = []
        for y in groups:
            if not current:
                current = [y]
                continue
            if len(current) < 5:
                avg_gap = np.mean(np.diff(current)) if len(current) > 1 else None
                gap = y - current[-1]
                if avg_gap is None or gap <= avg_gap * 1.6:
                    current.append(y)
                    continue
            if len(current) >= 4:
                if len(current) == 4:
                    sp = int(np.mean(np.diff(current)))
                    current.append(current[-1] + sp)
                staves.append(current[:5])
            current = [y]
        if len(current) >= 4:
            if len(current) == 4:
                sp = int(np.mean(np.diff(current)))
                current.append(current[-1] + sp)
            staves.append(current[:5])
        return staves
    def _detect_treble_staffs(self, gray):
        """
        Grand staff'ta treble clef'leri tespit eder.
        Treble ve bass arasındaki gap küçük (~200px),
        sistemler arası gap büyük (~300px+).
        """
        import numpy as np
        edges = cv2.Canny(gray, 30, 100)
        w = gray.shape[1]
        lines = cv2.HoughLinesP(edges, 1, np.pi/180,
            threshold=int(w*0.5), minLineLength=int(w*0.4), maxLineGap=30)
        if lines is None:
            return []
        h_lines = [l[0] for l in lines if abs(int(l[0][1])-int(l[0][3]))<4]
        raw_ys = sorted(set(int(l[1]) for l in h_lines))
        groups, group = [], [raw_ys[0]]
        for y in raw_ys[1:]:
            if y - group[-1] <= 8:
                group.append(y)
            else:
                groups.append(int(np.mean(group)))
                group = [y]
        groups.append(int(np.mean(group)))

        # 5'li gruplar = stafflar
        all_staffs = self._group_staff_lines(groups)

        # Spacing tutarlı olanları al (15-30px)
        valid = [s for s in all_staffs
                 if 15 <= int(np.mean(np.diff(s))) <= 30]

        if len(valid) < 2:
            return valid

        # Grand staff tespiti:
        # Treble-bass arası gap küçük, sistem arası gap büyük
        # Her çift staffın ilkini (treble) al
        treble_staffs = []
        i = 0
        while i < len(valid):
            treble_staffs.append(valid[i])
            # Sonraki staff bass mi? (gap < spacing*15 ise bass)
            if i+1 < len(valid):
                gap = valid[i+1][0] - valid[i][-1]
                spacing = int(np.mean(np.diff(valid[i])))
                if gap < spacing * 15:  # Bass staff, atla
                    i += 2
                else:
                    i += 1
            else:
                i += 1

        return treble_staffs[:4]

    def _detect_notes_in_staff(self, gray_raw, staff_ys, spacing):
        import numpy as np
        pad = spacing * 3
        y1 = max(0, min(staff_ys) - pad)
        y2 = min(gray_raw.shape[0], max(staff_ys) + pad)
        x_start = int(gray_raw.shape[1] * 0.15)  # %15 sol kenar = clef/imza geç
        crop = gray_raw[y1:y2, x_start:]

        _, binary = cv2.threshold(crop, 127, 255, cv2.THRESH_BINARY_INV)
        kh = cv2.getStructuringElement(cv2.MORPH_RECT, (spacing*5, 1))
        no_staff = cv2.subtract(binary, cv2.morphologyEx(binary, cv2.MORPH_OPEN, kh))
        kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, spacing*2))
        no_stems = cv2.subtract(no_staff, cv2.morphologyEx(no_staff, cv2.MORPH_OPEN, kv))

        staff_local = [y-y1 for y in staff_ys]
        top = min(staff_local) - spacing*2
        bot = max(staff_local) + spacing*1.5
        first_line_y = max(staff_local)

        def find_blobs(min_h_ratio):
            cnts,_ = cv2.findContours(no_stems, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            notes = []
            for cnt in cnts:
                x,y,w,h = cv2.boundingRect(cnt)
                area = cv2.contourArea(cnt)
                cx,cy = x+w//2, y+h//2
                aspect = w/h if h>0 else 0
                if (area>40 and area<spacing*spacing*3 and top<cy<bot and w>8
                        and h>spacing*min_h_ratio and h<spacing*2.3 and 0.5<aspect<2.5):
                    step = math.floor((first_line_y-cy)/(spacing/2))
                    step = max(-4, min(12, step))
                    nm,oc,midi = self.TREBLE_MAP.get(step, ('C',4,60))
                    notes.append({'cx':cx+x_start,'cy':cy,
                                  'pitch':f'{nm}{oc}','midi':midi})
            notes.sort(key=lambda n:n['cx'])
            merged, px = [], -999
            for n in notes:
                if n['cx']-px >= spacing*1.2:
                    merged.append(n); px=n['cx']
            return merged

        primary = find_blobs(0.5)
        secondary = find_blobs(0.25)
        for n in secondary:
            if not any(abs(n['cx']-p['cx'])<spacing for p in primary):
                primary.append(n)
        primary.sort(key=lambda n:n['cx'])
        return primary

    def _detect_tempo_pdf(self, gray_raw) -> int:
        try:
            import pytesseract, re
            region = gray_raw[:200, :]
            big = cv2.resize(region, (region.shape[1]*2, region.shape[0]*2),
                             interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh, config='--psm 6')
            numbers = re.findall(r'\d{2,3}', text)
            valid = [int(n) for n in numbers if 40<=int(n)<=240]
            return valid[0] if valid else 120
        except Exception:
            return 120

    def _detect_time_sig_pdf(self, gray_raw) -> str:
        try:
            import pytesseract, re
            region = gray_raw[300:600, :150]
            big = cv2.resize(region, (region.shape[1]*4, region.shape[0]*2),
                             interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh,
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789')
            digits = re.findall(r'\d', text)
            if len(digits)>=2:
                num,den = int(digits[0]),int(digits[1])
                if 2<=num<=12 and den in (2,4,8,16):
                    return f'{num}/{den}'
        except Exception:
            pass
        return '4/4'

    def _split_blob(self, mask_roi, min_dist_frac=0.35):
        """
        Birbirine yapışmış/birleşmiş nota kafalarını distance-transform
        ile ayırır. Her kafa merkezde daha 'kalın' olduğu için distance
        transform tepe noktaları ayrı kafalara denk gelir.
        Döndürür: [(cx, cy), ...] (mask_roi'nin lokal koordinatlarında)
        """
        if mask_roi.size == 0 or mask_roi.max() == 0:
            return []
        dist = cv2.distanceTransform(mask_roi, cv2.DIST_L2, 5)
        m = dist.max()
        if m <= 0:
            return []
        _, peaks = cv2.threshold(dist, m * min_dist_frac, 255, cv2.THRESH_BINARY)
        peaks = peaks.astype(np.uint8)
        n_labels, labels = cv2.connectedComponents(peaks)
        centers = []
        for lbl in range(1, n_labels):
            ys, xs = np.where(labels == lbl)
            if len(xs) < 3:
                continue
            centers.append((int(xs.mean()), int(ys.mean())))
        return centers
