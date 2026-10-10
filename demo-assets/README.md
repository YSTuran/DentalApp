# Demo STL dosyası

`synthetic-dental-arch-watertight.stl`, gerçek bir hastaya ait olmayan ve yalnızca
DentFlow iş akışını test etmek için üretilmiş sentetik bir dental ark modelidir.
Kapalı, manifold ve yüzey kesişimi içermeyen mesh olarak doğrulanır.

Dosyayı yeniden üretmek için backend dizininde şu komutu çalıştırın:

```powershell
.venv\Scripts\python.exe -m app.cli.generate_demo_stl
```

Bu model eğitim, tanı veya gerçek üretim amacıyla kullanılmamalıdır.
