<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1,maximum-scale=8,minimum-scale=0.1">
<script src="jquery-2.1.0.min.js"></script>
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

.modified {
    color: #d00;
    font-weight: bold;
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
</section>

<div id="jsontest">
</div>

<input type="button" id="savebutton" value="Save"/>

</body>

<script type="html/num_input">
<div id="{id}">
<span class="existing">{title} <span id="oldvalue">{oldvaluetext}{unit}</span></span>
<br/>
<input type="text" class="input" name="input_{name}" />
<input type="button" class="button_down" value="-"/>
<input type="button" class="button_up" value="+"/>
</div>
</script>

<script type="html/yesno_button">
<div id="{id}">
<span class="existing">{title} <span id="oldvalue">{oldvaluetext}</span></span>
<br/>
<input type="button" class="button_no" value="No"/>
<input type="button" class="button_yes" value="Yes"/>
</div>
</script>

<script>

function Setter(params) {
    var self = $.observable(this);

    self.params = params;

    $.each(self.params, function(idx, param) {
        param.id = "param_id_" + idx;
        param.oldvalue = param.value
        if (typeof(param.oldvalue) == "boolean")
        {
            param.oldvaluetext = param.oldvalue ? "Yes" : "No";
        }
        else
        {
            param.oldvaluetext = param.oldvalue;
        }
    });

    self.edit = function(param, newvalue) {
        param.value = newvalue;
        params[param.name] = param;
        self.trigger("edit", param);
    }

    self.adjust = function(param, updown) {
        // XXX increment
        param.value += (param.amount*updown);
        self.trigger("edit", param);
    }

    self.save = function() {
        var j = JSON.stringify(self.params);
        self.trigger("saved", j)
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
        set_text_state(el, param);
    }
    else if (param.kind === "yesno")
    {
        set_button_state(el, param.value);
    }
    var same;
    switch (typeof(param.oldvalue))
    {
        case "boolean":
            same = ((!param.value) == (!param.oldvalue));
            break;
        case "number":
            same = Math.abs(param.value - param.oldvalue) < 1e-3 * param.amount;
            break;
        default:
            same = (param.value === param.oldvalue);
    }

    $("#oldvalue", el).toggleClass("modified", !same);
});

setter.on("saved", function(j) {
    $("#jsontest").text(j);
});



$.route(function(hash) {

// clear list and add new ones
root.empty() && $.each(setter.params, function (idx, p) {
    add(p);

    $("#savebutton").click(function() {
        setter.save();
    })
})
})

function set_text_state(el, param)
{
    var input = $(".input", el);
    var s = Number(param.value).toFixed(param.digits)
    input.text(s).val(s)
}

function set_button_state(el, value)
{
    $(".button_yes", el).toggleClass("onbutton", value);
    $(".button_no", el).toggleClass("onbutton", !value);
}

function add(param)
{
    if (param.kind === "number")
    {
        var el = $($.render(number_template, param)).appendTo(root);
        var input = $(".input", el);

        input.keyup(function(e) {
            if (e.which == 13)
            {
                setter.edit(param, Number(this.value));
            }
        });

        input.blur(function(e) {
            setter.edit(param, Number(this.value));
        });

        $(".button_up", el).click(function() {
            setter.adjust(param, 1);
            this.blur()
        });
        $(".button_down", el).click(function() {
            setter.adjust(param, -1);
            this.blur()
        });

        set_text_state(el, param);
    }
    else if (param.kind === "yesno")
    {
        var el = $($.render(button_template, param)).appendTo(root);
        var button_yes = $(".button_yes", el);
        var button_no = $(".button_no", el);

        button_yes.click(function() {
            setter.edit(param, true);
            this.blur()
        })

        button_no.click(function() {
            setter.edit(param, false);
            this.blur()
        })

        set_button_state(el, param.value);
    }
}

})()

</script>

</html>
