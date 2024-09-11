## select all *.wav files from wav dir and pass to transcriber
## the result is *.wav.txt

source liepa_ausys.env
wav_path=$liepa_ausys_wav_path

if [ -z "${liepa_ausys_wav_path}" ]; then
    echo "liepa_ausys_wav_path is not set in liepa_ausys.env"; exit 1;
fi


ls -1 $wav_path | xargs -n1 -P6 ./transcriber.sh
