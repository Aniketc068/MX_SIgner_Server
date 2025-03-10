# Available date formats
date_formats = {
    'dd-MMM-yyyy': '%d-%b-%Y',  # 22-Nov-2024
    'dd-MMM-yy': '%d-%b-%y',  # 22-Nov-24
    'd-MMM-yyyy': '%d-%b-%Y',  # 2-Nov-2024
    'd-MMM-yy': '%d-%b-%y',  # 2-Nov-24
    'dd-MMM-yyyy HH:mm:ss': '%d-%b-%Y %H:%M:%S',  # 22-Nov-2024 15:30:45
    'dd-MMM-yyyy hh:mm:ss a': '%d-%b-%Y %I:%M:%S %p',  # 22-Nov-2024 03:30:45 PM
    'dd-MMM-yyyy h:mm a': '%d-%b-%Y %I:%M %p',  # 22-Nov-2024 3:30 PM
    'dd-MMM-yyyy EEEE': '%d-%b-%Y %A',  # 22-Nov-2024 Friday
    'dd-MMM-yyyy, EEEE': '%d-%b-%Y, %A',  # 22-Nov-2024, Friday
    'd-MMM-yyyy hh:mm:ss a': '%d-%b-%Y %I:%M:%S %p',  # 2-Nov-2024 03:30:45 PM
    'dd/MMM/yyyy': '%d/%b/%Y',  # 22/Nov/2024
    'dd-MMM-yyyy hh:mm:ss': '%d-%b-%Y %I:%M:%S',  # 22-Nov-2024 03:30:45
    'MMM-dd-yyyy': '%b-%d-%Y',  # Nov-22-2024
    'MMM-dd-yy': '%b-%d-%y',  # Nov-22-24
    'MMM d, yyyy': '%b %d, %Y',  # Nov 22, 2024
    'MMM d, yyyy h:mm a': '%b %d, %Y %I:%M %p',  # Nov 22, 2024 3:30 PM
    'MMMM dd, yyyy': '%B %d, %Y',  # November 22, 2024
    'MMM yyyy': '%b %Y',  # Nov 2024
    'yyyy-MMM-dd': '%Y-%b-%d',  # 2024-Nov-22
    'yyyy-MM-dd': '%Y-%m-%d',  # 2024-11-22 (ISO 8601)
    'MM/dd/yyyy': '%m/%d/%Y',  # 11/22/2024 (USA)
    'dd/MM/yyyy': '%d/%m/%Y',  # 22/11/2024 (Europe, Asia)
    'yyyy/MM/dd': '%Y/%m/%d',  # 2024/11/22 (Japan, China)
    'dd-MM-yyyy': '%d-%m-%Y',  # 22-11-2024 (Common in many countries)
    'MM-dd-yyyy': '%m-%d-%Y',  # 11-22-2024 (Common in the USA)
    'dd.MM.yyyy': '%d.%m.%Y',  # 22.11.2024 (Common in Central and Eastern Europe)
    'yyyy.MM.dd': '%Y.%m.%d',  # 2024.11.22 (Common in China, Japan)
    'd MMMM yyyy': '%d %B %Y',  # 22 November 2024 (Common in UK, others)
    'dd/MM/yyyy HH:mm': '%d/%m/%Y %H:%M',  # 22/11/2024 15:30 (Europe, Asia)
    'MM.dd.yyyy': '%m.%d.%Y',  # 11.22.2024 (Common in USA)
    'yyyy-dd-MM': '%Y-%d-%m',  # 2024-22-11 (Common in some countries)
    'd MMM, yyyy': '%d %b, %Y',  # 22 Nov, 2024 (Common in India)
}
