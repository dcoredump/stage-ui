#!/bin/bash

declare -a instruments

containsElement () {
  local e match="$1"
  shift
  for e; do [[ "$e" == "$match" ]] && return 0; done
  return 1
}

for lv2path in `echo $LV2_PATH | sed -e "s/:/ /g"`
do
    find "${lv2path}" -name "*.ttl" | while read ttl
    do
        instrument=`grep -l lv2:InstrumentPlugin "${ttl}"`
        if [ ! -z "${instrument}" ]
        then
            if [[ `containsElement "${instrument}" "${instruments[@]}"` != 1 ]]
            then
                instruments+=($instrument)
                uri=`cat ${instrument} | gawk '
BEGIN { uri="" }
/^<(.+)>\s*$/ { uri=$1 }
/lv2:InstrumentPlugin/ { print uri; exit }
' | sed -E "s/<//" | sed -E "s/>//"`
                instrument=`basename ${instrument}`
                #echo "${instrument} <${uri}>"
                preset=`lv2info "${uri}" 2>/dev/null | gawk '
/^\s*(.+$)/           { if (p_flag==1) print $0 }
/^\s*Presets:/ { p_flag=1 }
/^\s*$/        { p_flag=0 }
' | sed -E 's/^\s+//'`
                echo "${preset}" | while read p
                do
                    echo "instrument['${uri}'].append('${p}')"
                done
            fi
        fi
    done
done
