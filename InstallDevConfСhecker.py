from skytelDB import jarvisDB
import paramiko
from pythonping import ping
import socket
from mac_vendor_lookup import MacLookup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds",
         'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"
         ]

creds = ServiceAccountCredentials.from_json_keyfile_name(r"creds.json", scope)
client = gspread.authorize(creds)
sheet_DATA = client.open("Device Config Checker").worksheet("DATA")

task_ids_range = sheet_DATA.col_values(1)

if task_ids_range == [] or len(task_ids_range) == 1:
    task_ids = ['987987445', '645566444']
else:
    task_ids = task_ids_range

query_data = jarvisDB.Query(
    f"""
SELECT d1.TaskID,
       d1.OrderID,
       d1.AccID,
       d1.MAC,
       d1.IP,
       d1.PayId,
       d1.GroupID,
       d1.GroupName,
       d1.EndDAte,
       d1.ChekDate
FROM (
         SELECT nt.id                                        AS TaskID,
                nto.id                                       AS OrderID,
                na.id                                        AS AccID,
                na.mac                                       AS MAC,
                na.ip                                        AS IP,
                na.payID                                     AS PayId,
                ntg.id                                       AS GroupID,
                ntg.name                                     AS GroupName,
                COUNT(na.id)                                 AS TasksN,
                DATE_FORMAT(nt.dateEnd, '%d-%m-%Y %H:%i:%S') AS EndDAte,
                DATE_FORMAT(NOW(), '%d-%m-%Y %H:%i:%S')      AS ChekDate
         FROM jarvisdb.ns_tasks nt
                  LEFT JOIN jarvisdb.ns_accounts na ON nt.aID = na.id
                  LEFT JOIN jarvisdb.ns_tasks_orders nto ON nt.id = nto.taskID
                  LEFT JOIN jarvisdb.ns_tasks_groups ntg ON nt.groupID = ntg.id
         WHERE nto.id <> ''
           AND nt.status = 1
           AND nto.technologyID = 0
           AND nt.dateEnd BETWEEN (NOW() - INTERVAL 48 HOUR) AND (NOW() - INTERVAL 2 HOUR)
           AND LENGTH(na.mac) = 17
           AND na.mac LIKE '%:%'
           AND na.ip <> ''
#            AND na.ip = '10.80.8.48'
           AND nt.id NOT IN {tuple(task_ids)}
         GROUP BY nt.id
         ORDER BY nt.dateEnd
     ) d1
WHERE d1.TasksN = 1
"""
)

# last_task_id_cell = len(sheet_DATA.col_values(1)) + 1
# sheet_DATA.update(f"A{last_task_id_cell}:I", query_data)

ubiquitipass = [['ubnt', 'ubnt1'], ['admin', 'q1w2Admin'], ['ubnt', 'q1w2Admin'], ['wrong', 'pass']]
microtikpass = [['admin', 'admin1'], ['wrong', 'pass']]
chain_signal_difference = 5

LiteBeam_5ACconf = ['radio.1.countrycode=511\n', 'radio.1.txpower=24\n', 'radio.1.scan_list.status=disabled\n', 'radio.1.reg_obey=disabled\n', 'wireless.1.wds.status=enabled\n',
                    'netconf.2.ip=192.168.15.1\n']
MikrotikConf = ['192.168.15.1/24']

UbiquitiOtherConf = ['radio.1.countrycode=511\n', 'radio.1.txpower=25\n', 'wireless.1.wds.status=enabled\n', 'netconf.2.ip=192.168.15.1\n',
                     'wireless.1.scan_list.status=disabled\n']
datalen = len(query_data)

n = 0
print(f"Devices - {datalen}")
for i in query_data:
    n += 1
    print("-------------------------------------")
    print(f"{n})    {i[4]}")
    last_task_id_cell = len(sheet_DATA.col_values(1)) + 1
    try:
        p = ping(i[4])
        if str(p)[0:5] == 'Reply':
            a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            location = (i[4], 22)
            result_of_check = a_socket.connect_ex(location)
            if result_of_check == 0:
                port = 'open'
                vendor = MacLookup().lookup(i[3])
                print(vendor)
                if vendor == 'Ubiquiti Networks Inc.':
                    for u in ubiquitipass:
                        if len(ubiquitipass) == ubiquitipass.index([str(u[0]), str(u[1])]) + 1:
                            print("Wrong Password")
                            sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["Wrong Password!"]])
                            break
                        else:
                            try:
                                client = paramiko.SSHClient()
                                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                try:
                                    connect = client.connect(i[4], username=u[0], password=u[1])
                                except:
                                    continue
                                #     print(f"Connection Error, Maybe Not Stable Ping - {str(p)[str(p).find('Round')+17:]}")
                                #     sheet_DATA.update(f"A{last_task_id_cell}:K", [i + [f"Connection Error, Maybe Not Stable Ping - {str(p)[str(p).find('Round')+17:]}"]])
                                if [connect][0] == None and u in [['ubnt', 'ubnt1'], ['admin', 'q1w2Admin'], ['ubnt', 'q1w2Admin']]:

                                    stdin, stdout, stderr = client.exec_command("wstalist | grep '\"signal\"'")
                                    signal = stdout.readlines()

                                    print(signal)
                                    print(len(signal))

                                    if len(signal) == 3:
                                        signal1 = int(signal[0][-4:-2])
                                        signal2 = int(signal[2][-4:-2])
                                    else:
                                        signal1 = int(signal[0][2:-2].split(",")[11][-2:])
                                        signal2 = int(signal[0][2:-2].split(",")[328][-2:])

                                    print(signal1)
                                    print(signal2)

                                    if signal1 >= signal2:
                                        difference = signal1 - signal2
                                    else:
                                        difference = signal2 - signal1

                                    if chain_signal_difference < difference:
                                        print(f"Signal Difference Is High: {-difference}")
                                        sheet_DATA.update(f"A{last_task_id_cell}:K", [i + [f"TX Signal: {-signal1} / RX Signal: {-signal2} / Signal Difference: {-difference}"]])
                                        break
                                    else:
                                        stdin, stdout, stderr = client.exec_command("cat /var/etc/board.info | grep board.name")
                                        modelname = stdout.readlines()[0][11:23]
                                        print(modelname)

                                        if modelname == 'LiteBeam 5AC':
                                            try:
                                                stdin, stdout, stderr = client.exec_command(
                                                    "cat /tmp/system.cfg | grep -E 'radio.1.countrycode=|radio.1.txpower=|radio.1.scan_list.status=|radio.1.reg_obey=|wireless.1.wds.status=|netconf.2.ip='")
                                                lines = stdout.readlines()
                                            except OSError or paramiko.SSHException or paramiko.transport or TimeoutError or paramiko.ssh_exception.SSHException or paramiko.ssh_exception.NoValidConnectionsError:
                                                print("SSHException, OSError 3")
                                                sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["SSHException, OSError"]])
                                                break
                                            except:
                                                sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["SSHException, OSError"]])
                                                break

                                            wrong_config = set(lines) - set(LiteBeam_5ACconf)
                                            right_config = set(LiteBeam_5ACconf) - set(lines)

                                            print(f'Wrong Config >>>> {list(wrong_config)}')
                                            print(f'Right Config >>>> {list(right_config)}')
                                            sheet_DATA.update(f"A{last_task_id_cell}:K",
                                                              [i + [f'Wrong Config >>>> {list(wrong_config)} ||| Right Config >>>> {list(right_config)}']])

                                            stdin.close()
                                            client.close()
                                            break
                                        else:
                                            stdin, stdout, stderr = client.exec_command(
                                                "cat /tmp/system.cfg | grep -E  'radio.1.countrycode=|radio.1.txpower=|wireless.1.wds.status=|netconf.2.ip=|wireless.1.scan_list.status='")
                                            lines = stdout.readlines()

                                            wrong_config = set(lines) - set(UbiquitiOtherConf)
                                            right_config = set(UbiquitiOtherConf) - set(lines)

                                            if len(wrong_config) == 0:
                                                print(f"The Configuration is Correct: {vendor}")
                                                sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["The Configuration is Correct"]])
                                                break
                                            else:
                                                print(f'Wrong Config >>>> {list(wrong_config)}')
                                                print(f'Right Config >>>> {list(right_config)}')
                                                sheet_DATA.update(f"A{last_task_id_cell}:K",
                                                                  [i + [f'Wrong Config >>>> {list(wrong_config)} ||| Right Config >>>> {list(right_config)}']])
                                                break

                                            stdin.close()
                                            client.close()
                            except OSError or paramiko.SSHException or paramiko.transport or TimeoutError or paramiko.ssh_exception.SSHException or paramiko.ssh_exception.NoValidConnectionsError:
                                print("SSHException, OSError")
                elif vendor == 'Routerboard.com':
                    for m in microtikpass:
                        if len(microtikpass) == microtikpass.index([str(m[0]), str(m[1])]) + 1:
                            print("Wrong Password")
                            sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["Wrong Password!"]])
                            break
                        else:
                            try:
                                client = paramiko.SSHClient()
                                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                connect = client.connect(i[4], username=m[0], password=m[1])

                                if [connect][0] == None:
                                    stdin, stdout, stderr = client.exec_command(
                                        "put [/interface wireless registration-table get 0 tx-signal-strength];  put [/interface wireless registration-table get 0 signal-strength]")
                                    signal = stdout.readlines()

                                    signal1 = int(signal[0][1:3])
                                    signal2 = int(signal[1][1:3])
                                    if signal1 >= signal2:
                                        difference = signal1 - signal2
                                    else:
                                        difference = signal2 - signal1

                                    if chain_signal_difference < difference:
                                        print(f"Signal Difference Is High: {-difference}")
                                        sheet_DATA.update(f"A{last_task_id_cell}:K", [i + [f"TX Signal: {-signal1} / RX Signal: {-signal2} / Signal Difference: {-difference}"]])
                                        break
                                    else:
                                        stdin, stdout, stderr = client.exec_command("put [ip address get 0 value-name=address]")
                                        lines = stdout.readlines()

                                        wrong_config = set([lines[0][:-2]]) - set(MikrotikConf)
                                        right_config = set(MikrotikConf) - set([lines[0][:-2]])

                                        if len(wrong_config) == 0:
                                            print(f"The Configuration is Correct: {vendor}")
                                            sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["The Configuration is Correct."]])
                                            break
                                        else:
                                            print(f'Wrong Config >>>> {list(wrong_config)}')
                                            print(f'Right Config >>>> {list(right_config)}')
                                            sheet_DATA.update(f"A{last_task_id_cell}:K",
                                                              [i + [f'Wrong Config >>>> {list(wrong_config)} ||| Right Config >>>> {list(right_config)}']])
                                            break

                                    stdin.close()
                                    client.close()
                                    continue
                                else:
                                    print("Wromg Password!")
                                    sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["Wrong Password!"]])
                                    client.close()
                                    continue
                            except OSError or paramiko.SSHException or paramiko.transport or TimeoutError or paramiko.ssh_exception.SSHException or paramiko.ssh_exception.NoValidConnectionsError:
                                print("SSHException, OSError 7")
                                continue
                else:
                    sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["Mac Vendor is Not Identified."]])
                    print(f"Other Device {i[4]} >>>> {vendor}")
                    a_socket.close()
                    continue
            else:
                port = 'not open'
                print(f"SSH Port Is Not Open. >>>> {i[4]}")
                sheet_DATA.update(f"A{last_task_id_cell}:K", [i + ["SSH Port Is Not Open."]])
                a_socket.close()
                continue
        else:
            print(f"Device Not Ping >>>> {i[4]}")
            sheet_DATA.update(f"A{last_task_id_cell}:K", [i + [f"Device Not Ping"]])
            continue
    except:
        p = 'None'
        port = 'not open'

    print("-------------------------------------")
    continue
