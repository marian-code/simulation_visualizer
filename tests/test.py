import re

URL_NUM = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d*"
URL_STR = r".*?/visualize"
URL_LOC = r"localhost:\d+"
# find string or ip address
URL = r"https?://(?:" + URL_NUM + r"|" + URL_STR + r"|" + URL_LOC + r")"
# string component that can contain special characters ending with question mark,
# may or may not be present
PATH_COMP = r"(?:(\S*?)\?|/)?"
# parameters component 2-string with '=' and '&' symbols
# with 0 or more occurences
PARAM_COMP = r"((?:\S+=\S+&?){0,})"
# server component is just a plain string
# negative lookahed ensures that we match the last one '#'
SERVER_COMP = r"#(?!.*#)(.*)"
DATA = PATH_COMP + PARAM_COMP + SERVER_COMP
URL_FIND = re.compile(URL + DATA)
PARAM_FIND = r"{}=(\S*?)(?:&|\Z)"

url = "https://simulate.duckdns.org/visualize/home/rynik/ace/btin2cd_pace_100/COLVAR?x=time&y=u_cn&z=u_vol&t=time&dim=2D#kohn"
data = URL_FIND.findall(url)[0]

print(data)