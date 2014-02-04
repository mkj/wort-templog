<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<script src="jquery-2.1.0.js"></script>
<script>
%include riot.min.js
</script>

<style type="text/css">
span.no_selection {
    -webkit-user-select: none; // webkit (safari, chrome) browsers
    -moz-user-select: none; // mozilla browsers
    -khtml-user-select: none; // webkit (konqueror) browsers
}

body {
    font-family: "sans-serif";
}

input {
    border: 2px solid transparent;
    border-radius: 4px;
    background-color: white;
    border-color: black;
    padding: 0;
    font-size: 80%;
}

input[type="button"] {
    width: 4em;
    height: 4em;
    margin-left: 0.5em;
}

input[type="submit"] {
    width: 10em;
    height: 4em;
    margin-top: 1em;
    align: center;
}

input[type="text"] {
    height: 4em;
    text-align: center;
}

.onbutton {
    background-color: #cdf;
}

.existing {
    margin-top: 1em;
    font-size: 70%;
}

</style>
<title>Set templog</title>
</head>

<body>

<section id="paramlist">
</div>

</body>

<script type="html/num_input">
<div id="{id}">
<span class="existing">{title} <span id="existing_{name}">{oldvalue}</span>{unit}</span>
<br/>
<input type="text" id="input" name="input_{name}" />
<!--
<input type="button" class="button_down" id="down" name="down_{name}" value="-" "/>
<input type="button" class="button_up" id="up" name="up_{name}" value="+" "/>
-->
</div>
</script>

<script type="html/yesno_button">
<div id="{id}">
<span class="existing">{title} <span id="existing_{name}">{oldvalue}</span></span>
<br/>
<input type="button" class="button_no" id="no_{name}" name="no_{name}" value="No"/>
<input type="button" class="button_yes" id="yes_{name}" name="yes_{name}" value="Yes"/>
</div>
</script>

<script>

function Setter(params) {
    var self = $.observable(this);

    self.params = params;

    $.each(self.params, function(idx, param) {
        param.id = "param_id_" + idx;
    });

    self.edit = function(param) {
        params[param.name] = param;
        self.trigger("edit", param);
    }

    self.adjust = function(param, updown) {
        // XXX increment
        self.trigger("edit", param);
    }

}

(function() { 'use strict';

var params = {{!inline_data}};
window.setter = new Setter(params);

var root = $("#paramlist");

var number_template = $("[type='html/num_input']").html();
var button_template = $("[type='html/yesno_button']").html();

setter.on("add", add);
setter.on("edit", function(param)
{
    var el = $("#" + param.id);
    if (param.kind === "number")
    {
        $(".input", el).text(param.value).value(param.value);
    }
    else if (param.kind === "yesno")
    {
        set_state(el, param.value);
    }
})

$.route(function(hash) {

// clear list and add new ones
root.empty() && $.each(setter.params, function (idx, p) {
    add(p);
})
})

function set_state(el, value)
{
    var button_yes = $(".button_yes", el);
    var button_no = $(".button_no", el);
    if (value)
    {
        button_yes.addClass("onbutton");
        button_no.removeClass("onbutton");
    }
    else
    {
        button_no.addClass("onbutton");
        button_yes.removeClass("onbutton");
    }
}

function add(param)
{
    if (param.kind === "number")
    {
        var el = $($.render(number_template, param)).appendTo(root);
        var input = $(".input", el);
    }
    else if (param.kind === "yesno")
    {
        var el = $($.render(button_template, param)).appendTo(root);
        var button_yes = $(".button_yes", el);
        var button_no = $(".button_no", el);

        button_yes.click(function() {
            param.value = true;
            setter.edit(param);
        })

        button_no.click(function() {
            param.value = false;
            setter.edit(param);
        })

        set_state(el, param.value);
    }
}

})()

</script>

</html>
