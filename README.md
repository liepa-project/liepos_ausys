# Liepos Ausys

Pagrindė info: https://github.com/airenas/list

Klientas transkribavimui. Tikrinta tik ant Ubuntu. Įrankis siunčia bylas į serverį iš lokalaus kompiuterio disko. Po sėkmingo transkribavimo tekstinis failas yra sukuriamas toje pačioje direktorijoje kaip ir garsinis signalas.

## Naudojamas

* Parsisiųsti arba klonuoti šią repozitoriją
* Pakeisti turinį bylos: `liepa_ausys.env`
  * `liepa_ausys_url` - kur yra nutlęs atpažinimo serveris
  * `liepa_ausys_auth` - prisijungimo detalės
  * `liepa_ausys_wav_path` - nurodyti kur yra audio failai lokaliame kompiuteryje
 
### Transkribavimo pavyzdys

`liepa_ausys_wav_path` paliekame nustatymą: `wav/*.wav`. Į `wav` direktoriją įkeliame `0.wav` bylą. Paleidžiam `./run.files.sh` skriptą. Jis nusiųs `0.wav` ir gavus atsakymą sukurs bylą `0.wav.txt`. Kurio turinys bus:

```
# 1 S0000
1 0 0.12 <eps>
1 0.12 0.33 Kad
1 0.33 1.29 statybininkai
1 1.29 2.34 pasistengs ,
1 2.34 2.4 <eps>
```
