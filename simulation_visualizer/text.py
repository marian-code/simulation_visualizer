from dash import html

PLUGINS_INTRO = (
    "This dashboard is extensible through parser plugins. Each plugin is one "
    "self-contained parser that is able to extract data of specific format. "
    "Here follows the list of currently present parsers:"
)

URL_SHARING = (
    "One can notice that all actions in the control tab are reflected in the "
    "url. The url has three components: #hash - corresponding to host name at "
    "the end of the url. '/some/path/to/my/file' that follows after the http "
    "address stores the path to file on remote server. Lastly querry string "
    "?x=something&y=something_else&dim=2D stores the graph parameters. The "
    "app can be started from such url and will take you right to the "
    "specified file and plot it with saved parameters."
)

# TODO update for more files
USAGE = [
    "The dasboard basic usage is this:",
    html.Br(),
    (
        "1. Select host PC in the dropdown menu where the file you wish to view "
        "is located."
    ),
    html.Br(),
    (
        "2. Next select the path to file on that server. The paths on remote "
        "server are auto-suggested. The suggestions should appear automatically "
        "and if not you can display them with arrow-down key on keyboard. The "
        "suggeestion dropdown menu might be too narrow for long paths in chromium "
        "based browsers, unfortunatelly, nothing can be done with that from the "
        "app side."
    ),
    html.Br(),
    (
        "3. After this click on the submit button and availabele data column "
        "labels will be loaded. Note that once data column labels are loaded "
        "and you wish to plot another file of same type, there is no need to "
        "click submit button again. It serves only to read data column labels."
    ),
    html.Br(),
    (
        "4. After this you can proceed with setting how you wish the graph to be "
        "plotted. Select 2D or 3D and appropriate columns for each axis. Note "
        "that for 'y' and 'z' axis you can select more than one label. Some "
        "parsers will also auto-suggest most suitable labels for convenience."
        "There is also a series option for both 2D and 3D. With this you are able to "
        "add a fourth dimension that will be represented as a slider under the graph."
        "By moving it you will be able to see 2D or 3D graph in different 'times'"
    ),
    html.Br(),
    (
        "5. Now you can click the plot button. The data will be read from remote "
        "server and stored into pandas dataframe. From this dataframe a plot "
        "will be generated by Dash server and sent to your browser. The plot "
        "might take some time to load especially for bigger files. You will see "
        "the file size after clicking the submit button. The data must be "
        "downloaded from server and than sent to your browser so please be "
        "patient. For files up to ~100MB it should be a matter of seconds. Each "
        "loaded pandas dataframe is cached by dash server for 10 minutes so "
        "ploting again in this window will be faster as data does not have to be "
        "downloaded again, but you will not see the most up-to-date file!"
    ),
    html.Br(),
    (
        "6. After plotting you can save the file to your PC by clicking the "
        "download button. You can select either CSV file or interactive plotly "
        "html file. Download can be also used without ploting the file in web-ui"
    ),
]