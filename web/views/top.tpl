<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<title>Wort Temperature Log</title>
<meta name="viewport" content="width=device-width">
<meta name="theme-color" content="#fff">
<style type="text/css">
span.no_selection {
    -webkit-user-select: none; // webkit (safari, chrome) browsers
    -moz-user-select: none; // mozilla browsers
    -khtml-user-select: none; // webkit (konqueror) browsers
}

span.codelink {
 font-size: 70%;
 text-align: right;
}

#mainimage {
	width: 100%;
	max-width: {{graphwidth}}px;
}
</style>
<title></title>
</head>
<script type="text/javascript">
function updatewidth() {
	var width_input = document.getElementById("scaledwidth");
	var main_image = document.getElementById("mainimage");
	width_input.value = main_image.clientWidth;
	return true;
}

</script>
<body>
<form action="" method="get" onsubmit="return updatewidth();">
<span class="no_selection"><input type="image" id="mainimage" src="{{graphdata}}"/></span>
<input type="hidden" name="length" value="{{length}}"/>
<input type="hidden" name="end" value="{{end}}"/>
<input type="hidden" name="zoom" value="yeah"/>
<input type="hidden" name="scaledwidth" id="scaledwidth" value="{{graphwidth}}"/>
</form>
<span class="codelink">Click to zoom in, click the left axis to zoom out. <a href="https://secure.ucc.asn.au/hg/templog/file/tip">Source code</a> for the Raspberry Pi controller and this web interface</a>. <a href="set">Adjustments</a> by phone.</span>
</body>
</html>
