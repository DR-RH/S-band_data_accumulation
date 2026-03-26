from decoder.adcs_HK_list_of_main import adcs_HK_list

index = []
moji = ""

for group in adcs_HK_list:
    fmt_raw = group[3]
    # if fmt_raw == '1' or fmt_raw == '2' or fmt_raw == '3':
    #     fmt = 'B'
    # else:
    fmt = fmt_raw
    moji += fmt

    index.append(group[0])
#     print(group[2])
# print(index)
print(moji.upper())


