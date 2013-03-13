<#assign s=JspTaglibs["/WEB-INF/struts-tags.tld"] />
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<#include "../template/jquery_header.ftl"/>
    <style type="text/css">
        .error_msg_section {
            margin: 5px;
            width: 410px;
            text-align: left;
        }
    </style>
</head>
<body>
<div class="popup_main_div">
<#include "../template/action_errors.ftl" />

<@s.if test="%{licence.licenceType == 'tern'}">
    <div class="popup_title">
        TERN Licence
    </div>
    <div class="popup_spec">
        TERN licence spec:
    </div>
</@s.if>
<@s.else>
    <div class="popup_title">
        Define Your Own Licence
    </div>
    <div class="popup_spec">
        Please edit the data licence:
    </div>
</@s.else>
    <div class="licence_contents">
    <@s.if test="%{licence.licenceType == 'tern'}">
        <@s.textarea name="licence.Contents" cssClass="input_textarea" style="width: 460px; height: 240px;" id="plicence_contents"  readonly ="true" />
        <div class="comments">
            <@s.text name="licence.add.tern.licence.hint" />
        </div>
    </@s.if>
    <@s.else>
        <@s.textarea name="licence.Contents" cssClass="input_textarea" style="width: 460px; height: 240px;" id="plicence_contents" />
        <div class="comments">
            <@s.text name="licence.add.user.defined.licence.hint" />
        </div>
    </@s.else>
    </div>
    <div class="popup_button_div">
        <@s.hidden name="licence.licenceType" id="plicence_type"/>
        <input type="button" value="Back" class="input_button_style"
               onclick="window.location = '${base}/data/licenceOptions.jspx?collection.id=<@s.property value='collection.id' />&licence.licenceType=${licence.licenceType}';"> &nbsp;&nbsp;
        <input type="button" value="Save" id="saveLicence" class="input_button_style"/>
    </div>
</div>
</div>
</body>
</html>