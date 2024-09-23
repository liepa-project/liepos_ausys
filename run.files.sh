## select all *.wav files from wav dir and pass to transcriber
## the result is *.wav.txt

source liepa_ausys.env
wav_path=$liepa_ausys_wav_path

if [ -z "${liepa_ausys_wav_path}" ]; then
    echo "liepa_ausys_wav_path is not set in liepa_ausys.env"; exit 1;
fi

count=$(ls -1q $wav_path  | wc -l)

if (( $count == 0)) ; then
    echo "There is no files in $wav_path directory"; exit 1;
fi

ls -1 $wav_path | sed 's| |\\ |g' | xargs -n1 -P6 ./bin/transcriber.sh
