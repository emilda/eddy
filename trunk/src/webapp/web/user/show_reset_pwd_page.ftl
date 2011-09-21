<#assign s=JspTaglibs["/WEB-INF/struts-tags.tld"] />
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title><@s.text name="user.reset.passwd.action.title" /></title>

<#include "../template/header.ftl"/>

<script type="text/javascript">
function refresh()
{
	document.getElementById("imagevalue").src='${base}/captch/captchCode.jspx?now=' + new Date();
}
</script>
</head>

<body>
<!-- Navigation Section -->
<#include "../template/nav_section.ftl" />
<!-- Navigation Title -->
<div class="title_panel">
	<div class="div_inline">&nbsp;&nbsp;</div>
	<div class="div_inline"><img src="${base}/images/link_arrow.png" border="0"/></div>
	<div class="div_inline"><a href="${base}/user/user_request_resetpwd"><@s.text name="user.reset.passwd.action.title" /></a></div>
</div>
<div style="clear:both"></div> 
<!-- End of Navigation Title -->
<div class="main_body_container">
	<div class="main_body_big_left_panel">
	<br />
		<#include "../template/action_errors.ftl" />
 
		<div class="reg_panel">
            <div class="reg_middle_panel">
            <@s.form action="resetPassword.jspx" namespace="/user" method="post">
            <@s.hidden name="user.id" />
            <@s.hidden name="user.resetPasswdHashCode" />
            <@s.hidden name="user.email" />
            <@s.hidden name="user.displayName" />
            <table>
                <tr>
                    <td>
                    <div class="reg_field"><@s.text name="user.displayName" />:</div></td>
                    <td><@s.property value="user.displayName"/></td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td>
                    <div class="reg_field"><@s.text name="user.email" />:</div></td>
                    <td><@s.property value="user.email"/></td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td><div class="reg_field"><@s.text name="user.new.password" />:</div></td>
                    <td><@s.password name="user.password" cssClass="input_field" /></td>
                    <td><div class="reg_comment">* <@s.text name="user.new.password.hint" /></div></td>
                </tr>
                <tr>
                    <td><div class="reg_field"><@s.text name="user.new.rePassword" />:</div></td>
                    <td><@s.password name="rePassword" cssClass="input_field" /></td>
                    <td><div class="reg_comment">* <@s.text name="user.new.rePassword.hint" /></div></td>
                </tr>
                <tr><td><div class="reg_field"><@s.text name="security.code" />:</div></td>
                    <td><@s.textfield name="securityCode" cssClass="input_field" /></td>
                    <td><div class="reg_comment">* <@s.text name="security.code.hint" /></div>
                    </td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
                    <td align="center"><img src="${base}/captch/captchCode.jspx?now=new Date()" border="0" id="imagevalue" name="imagevalue" /></td>
                    <td><div class="reg_comment">&nbsp;<a href="#" onclick="refresh()"><img src="${base}/images/refresh.png" class="image_position" /> can't read this?</a></div></td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
                    <td>
                        <div class="input_button_div"><@s.submit value="%{getText('reset.password.button')}" cssClass="input_button_style" /> &nbsp; <@s.reset value="%{getText('reset.button')}" cssClass="input_button_style" /></div>
                    </td>
                    <td>&nbsp;</td>
                </tr>
            </table>
            </@s.form>
            </div>
	    </div>
	    <br/>
        <div class="reg_panel">
            <div class="reg_options_middle">
                <div class="use_policy">
                    This site is provided 'as is' by Monash University for use by Monash researchers and their research collaborators at other institutions. Use by Monash's research collaborators
                    is encouraged and welcomed. Use of this site by all users is subject to Monash University's normal Staff Acceptable Use Policy for IT Services (AUP) available
                    at:<a href="http://www.policy.monash.edu/policy-bank/management/its/it-use-policy-staff-and-authorised.html" target="_blank">www.policy.monash.edu/policy-bank/management/its/it-use-policy-staff-and-authorised.html</a>.
                    The Monash team leader of each research group is responsible for ensuring that the AUP is adhered to by all members of the group. Publication of information, information access controls,
                    group membership controls are the responsibility of the team leader of each worksite. Monash University does not warrant the accuracy of the information provided by the service, nor the
                    fitness for purpose of the service for your intended application. Data is stored and backed-up on the University's LaRDS research data store. Services are provided to 3rd parties on an 'all
                    care no responsibility' basis. Use of this site indicates your acceptance of these terms and conditions.
                 </div>
            </div>
        </div>
		<br/>
		<br/>
	</div>
	<div style="clear:both"></div> 	 		
</div>
<br/>
<#include "../template/footer.ftl"/>
</body>
</html>
