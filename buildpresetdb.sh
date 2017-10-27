#!/bin/bash

echo "#!/usr/bin/python3"
echo "instrument{}=[]"

for uri in `lv2ls 2>/dev/null`
do
    preset=`lv2info "${uri}" 2>/dev/null | gawk '
/^\s*(.+$)/           { if (p_flag==1) print $0 }
/^\s*Presets:/ { p_flag=1 }
/^\s*$/        { p_flag=0 }
' | sed -E 's/^\s+//'`
    echo "${preset}" | while read p
    do
        echo "instrument['${uri}'].append('${p}')"
    done
done
