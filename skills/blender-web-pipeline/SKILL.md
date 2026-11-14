---
name: blender-web-pipeline
description: Pola optimasi ekspor Blender → glTF/GLB untuk web & viewer three.js divisi: ekspor GLB, kompresi Draco, decimation, LOD, texture baking/downscale, batch headless. Dipakai saat menyiapkan aset GLB untuk slot GLTFLoader pipeline video 3D (pipeline-3d) atau viewer web. Adaptasi lokal dari skill blender-web-pipeline (freshtechbro/claudedesignskills, https://github.com/freshtechbro/claudedesignskills/blob/main/.claude/skills/blender-web-pipeline/SKILL.md; juga terdaftar di mcpmarket.com/tools/skills/blender-web-pipeline).
---

# Blender Web Pipeline (adaptasi lokal Moderate)

## Konteks lokal (WAJIB pakai jalur ini, bukan instalasi Blender generik)

- Blender 5.2.3 LTS: `~/workspace/divisi/branding-promosi/3d-agent/tools/blender/current/blender`
- Headless WAJIB via wrapper: `tools/blender/blender-headless` (VM tanpa libEGL sistem; EEVEE segfault → render final tetap three.js, Blender hanya preparasi aset).
- Runner produksi: `tools/blender-runner/blender_asset_runner.py` (spec JSON → GLB). Pola di skill ini adalah tahap OPTIMASI tambahan di atas runner itu, bukan penggantinya.
- Skill induk produksi video: `threejs-storyboard-production`. Aset hasil optimasi masuk lewat slot GLTFLoader viewer yang sama.

## Target metriks web (dari skill sumber)

- Ukuran file: <5 MB per model, ideal <1 MB (GLB karakter uji Quaternius saat ini ±8 MB → kandidat utama optimasi).
- Poligon: <50k segitiga untuk real-time.
- Tekstur: maks 2048×2048, disukai 1024×1024.
- Draw call: minimalkan via atlas tekstur.

## Pola ekspor GLB teroptimasi (bpy)

```python
bpy.ops.export_scene.gltf(
    filepath='/path/output.glb',
    export_format='GLB',
    export_apply=True,            # terapkan modifier
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_animations=True,       # pertahankan klip (idle/walk/talk dst.)
    export_cameras=False,
    export_lights=False,
)
```

## Kompresi Draco — PERINGATAN LOKAL

Parameter sumber: `export_draco_mesh_compression_enable=True`, level 6 (0–10), quantization position 14 / normal 10 / texcoord 12 (mode hemat ekstrem: level 8, 12/8/10).

**Jangan aktifkan Draco untuk aset pipeline video sebelum DRACOLoader + decoder Draco ter-vendor di viewer divisi dan teruji render frame-step-nya.** GLB Draco tanpa decoder = aset gagal muat. Untuk video (bukan web interaktif), decimation + downscale tekstur biasanya memberi penghematan yang cukup tanpa risiko decoder. Draco hanya untuk aset web interaktif yang viewernya memang menyiapkan `DRACOLoader.setDecoderPath()`.

## Decimation (kurangi poligon)

```python
dec = obj.modifiers.new(name='Decimate', type='DECIMATE')
dec.ratio = 0.5                  # 0.5 = 50% poligon asal
dec.use_collapse_triangulate = True
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_apply(modifier='Decimate')
```

Untuk karakter ber-rig/beranimasi: decimate merusak skinning bila diterapkan sembarangan — uji klip animasi sesudahnya di viewer (mixer deterministik) sebelum aset diterima.

## LOD (Level of Detail)

Duplikat objek per level rasio [0.75, 0.5, 0.25] sebagai `<nama>_LOD0/1/2`, decimate per level, ekspor sebagai GLB terpisah. Untuk pipeline video, LOD hanya relevan untuk objek latar jauh; karakter hero selalu LOD0.

## Texture downscale + ekspor hemat

```python
for img in bpy.data.images:
    if img.size[0] > 1024 or img.size[1] > 1024:
        img.scale(1024, 1024)
# saat ekspor: export_image_format='JPEG', export_jpeg_quality=85 (PNG bila butuh alfa/kualitas)
```

## Texture baking (Cycles CPU)

Satukan material kompleks ke satu tekstur COMBINED per objek (`bpy.ops.object.bake(type='COMBINED')`, image 1024/2048). Di VM ini baking Cycles CPU lambat — pakai hanya untuk objek hero statis, bukan batch besar.

## Batch headless

Pola sumber: `blender --background --python batch_export.py -- <dir_in> <dir_out>` — di sini selalu ganti `blender` dengan wrapper `blender-headless` dan arahkan skrip lewat runner bila memungkinkan.

## Urutan pakai yang disarankan (aset GLB masuk pipeline)

1. Impor/redesign aset (runner atau MCP resmi lokal).
2. Downscale tekstur >1024 → decimate seperlunya (karakter: uji animasi) → LOD hanya untuk latar.
3. Ekspor GLB non-Draco untuk video; catat ukuran + jumlah segitiga sebelum/sesudah.
4. Uji muat di viewer uji divisi + render klip pendek sebelum aset dinyatakan siap.
