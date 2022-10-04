import jinja2
import sys
import datetime
import bitmath
from urllib.parse import urlparse
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from io import BytesIO
from .bash import SH_TEMPLATE
from .powershell import POWERSHELL_TEMPLATE
from .python import PY_TEMPLATE

BULK_EXPLANATORY_NOTE = """\
CKAN Bulk Download
------------------

{title} {prefix}

Bulk download package generated: {timestamp}
Number of Packages             : {package_count}
Number of Resources            : {resource_count}
Total Space required           : {total_size}
Total Size (bytes)             : {total_size_bytes}

This archive contains the following files:

download.py:
Python 3 script, which when executed will download the files,
and then checksum them.  This script is cross platform and is supported
on Linux / MacOS / Windows hosts. Requires the `requests` module.

download.ps1:
Windows PowerShell script, which when executed will download the files,
and then checksum them. There are no dependencies other than PowerShell.

download.sh:
UNIX shell script, which when executed will download the files,
and then checksum them. This is supported on any Linux or MacOS/BSD
system, so long as `curl` is installed.

Before running either of these scripts, please set the CKAN_API_KEY
environment variable.

You can find your API Key by browsing to:
{user_page}

The API key has the format:
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
To set the environment variable in Linux/MacOS/Unix, use:
export CKAN_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

On Microsoft Windows, within Powershell, use:
$env:CKAN_API_KEY="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

QUERY.txt:
Text file which contains metadata about the download results and the original
query

tmp folder:
This folder contains files required by the download scripts. Its
contents can be ignored.


Note all CSV files are encoded as UTF-8 with a Byte Order Mark (BOM) to
enable character set detection by recent versions of Microsoft Excel.
"""

QUERY_TEMPLATE = """\
Title              : {title}
Prefix             : {prefix}
Timestamp          : {timestamp}
User Page          : {user_page}
Query              : {query}
QueryURL           : {query_url}
Download URL       : {download_url}
URL Count          : {url_count}
MD5 Sum Count      : {md5_count}
Package Count      : {package_count}
Resource Count     : {resource_count}
Total Space        : {total_size}
Total Bytes        : {total_size_bytes}
"""

def str_crlf(s):
    """
    convert string to DOS multi-line encoding (CRLF)
    """
    return s.replace("\n", "\r\n")


def get_timestamp():
    return datetime.datetime.now().strftime(
        "%Y-%m-%dT%H:%M:%S.%f%z"
    )



def generate_bulk_zip(
        pfx,
        title,
        username,
        user_page,
        packages,
        resources,
        query=None,
        query_url=None,
        download_url=None,
        md5_attribute="md5"):

    def ip(s):
        return pfx + "/" + s

    def write_script(filename, contents):
        info = ZipInfo(ip(filename))
        info.external_attr = 0o755 << 16  # mark script as executable
        contents = (
            jinja2.Environment()
            .from_string(contents)
            .render(
                user_page=user_page,
                md5sum_fname=md5sum_fname,
                urls_fname=urls_fname,
                prefix=pfx,
                username=username,
            )
        )
        zf.writestr(info, contents.encode("utf-8"))

    urls = []
    md5sums = []
    total_size_bytes = 0
    resource_count = len(resources)
    package_count = len(packages)

    for resource in sorted(resources, key=lambda r: r["url"]):
        url = resource["url"]
        urls.append(resource["url"])
        if "size" in resource:
            if resource["size"]:
                total_size_bytes = total_size_bytes + resource["size"]

        if md5_attribute in resource:
            filename = urlparse(url).path.split("/")[-1]
            md5sums.append((resource[md5_attribute], filename))

    fd = BytesIO()
    zf = ZipFile(fd, mode="w", compression=ZIP_DEFLATED)
    zf.writestr(
        ip("README.txt"),
        str_crlf(
            BULK_EXPLANATORY_NOTE.format(
                prefix=pfx,
                timestamp=get_timestamp(),
                title=title,
                user_page=user_page,
                total_size=bitmath.Byte(bytes=total_size_bytes).best_prefix(),
                resource_count=resource_count,
                package_count=package_count,
                total_size_bytes=total_size_bytes,
            )
        ),
    )

    urls_fname = "tmp/{}_urls.txt".format(pfx)
    md5sum_fname = "tmp/{}_md5sum.txt".format(pfx)

    zf.writestr(ip(urls_fname), "\n".join(urls) + "\n")
    zf.writestr(ip(md5sum_fname), "\n".join("%s  %s" % t for t in md5sums) + "\n")

    write_script("download.sh", SH_TEMPLATE)
    write_script("download.ps1", POWERSHELL_TEMPLATE)
    write_script("download.py", PY_TEMPLATE)

    zf.writestr(
        ip("QUERY.txt"),
        str_crlf(
            QUERY_TEMPLATE.format(
                prefix=pfx,
                timestamp=get_timestamp(),
                title=title,
                user_page=user_page,
                url_count=len(urls),
                md5_count=len(md5sums),
                query=query,
                query_url=query_url,
                download_url=download_url,
                package_count=package_count,
                resource_count=resource_count,
                total_size=bitmath.Byte(bytes=total_size_bytes).best_prefix(),
                total_size_bytes=total_size_bytes,
            )
        ),
    )

    zf.close()
    return fd.getvalue()
