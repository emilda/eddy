<#assign s=JspTaglibs["/WEB-INF/struts-tags.tld"] />
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title><@s.text name="user.register.option.title" /></title>

<#include "../template/header.ftl"/>

</head>
<body>
<!-- Navigation Section -->
<#include "../template/nav_section.ftl" />
<!-- Navigation Title -->
<div class="title_panel">
	<div class="div_inline">&nbsp;&nbsp;</div>
	<div class="div_inline"><img src="${base}/images/link_arrow.png" border="0"/></div>
	<div class="div_inline"><a href="${base}/user/register_options"><@s.text name="user.register.option.title" /></a></div>
</div>
<div style="clear:both"></div> 
<!-- End of Navigation Title -->
		
<div class="main_body_container">
	<div class="main_body_big_left_panel">
	<br />
		<#include "../template/action_errors.ftl" />		
        <div class="reg_options_div">
            <div class="reg_options_middle">
                <div>
                    <@s.text name="user.reg.choose.options.msg" />
                </div>
                <br/>
                <br/>
                <div class="blank_separator"></div>
                <div class="blank_separator"></div>
                <div class="blank_separator"></div>
                <div class="reg_choices">
				    <a href="${base}/user/ldap_user_register"><img src="${base}/images/mon_reg.png"  border="0" /> <strong><@s.text name="user.ldap.register.action.title" /></strong></a>
				</div>
                <div style="clear:both"></div>
                <div class="blank_separator"></div>
                <br/>
                <br/>
                <div class="blank_separator"></div>
                <div class="reg_choices">
				    <a href="${base}/user/user_register"><img src="${base}/images/self_reg.png" border="0" /> <strong><@s.text name="user.register.action.title" /></strong></a>
				</div>
                <div style="clear:both"></div>
                <br/>
            </div>
            <br/>
        </div>
        <br/>
	</div>
	<div style="clear:both"></div>  		
</div>
<br/>
<#include "../template/footer.ftl"/>
</body>
</html>
