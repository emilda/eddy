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
    <div class="popup_title">
        Add an associated researcher
    </div>
<@s.if test="%{actionSuccessMsg != null}">
    <div class="content_none_border_div">
        <div class="none_border_block">
            <#include "../template/action_success_msg.ftl"/>
        </div>
    </div>
</@s.if>
<@s.form action="addUDParty.jspx" namespace="/data" method="post">
    <@s.hidden name="searchCnOrEmail" />
    <div class="popup_row">
        <div class="popup_spec">
            Please enter a researcher information bellow:
        </div>

        <div class="content_none_border_div">
            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Title:
                </div>
                <div class="popup_input_value_section">
                    <@s.textfield name="selectedPartyBean.personTitle" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.title.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>
            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    First Name:
                </div>
                <div class="popup_input_value_section">
                    <@s.textfield name="selectedPartyBean.personGivenName" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.first.name.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Last Name:
                </div>
                <div class="popup_input_value_section">
                    <@s.textfield name="selectedPartyBean.personFamilyName" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.last.name.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Email:
                </div>
                <div class="popup_input_value_section">
                    <@s.textfield name="selectedPartyBean.email" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.email.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Address:
                </div>
                <div class="popup_input_value_section">
                    <@s.textarea name="selectedPartyBean.address"  cssClass="input_textarea" style="width: 300px; height: 80px;" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.address.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Web URL:
                </div>
                <div class="popup_input_value_section">
                    <@s.textfield name="selectedPartyBean.url" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.url.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Description:
                </div>
                <div class="popup_input_value_section">
                    <@s.textarea name="selectedPartyBean.description"  cssClass="input_textarea" style="width: 300px; height: 80px;" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.desc.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Group Name:
                </div>
                <div class="popup_input_value_section">
                    <@s.select id="groupName" name="selectedPartyBean.groupKey" headerKey="${selectedPartyBean.groupKey}" list="organizations" cssClass="input_select_field" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.group.name.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>

            <div class="popup_input_div">
                <div class="popup_input_field_title">
                    Group Web Site:
                </div>
                <div class="popup_input_value_section">
                    <@s.textfield name="selectedPartyBean.originateSourceValue" />
                    <div class="comments">
                        <@s.text name="ands.add.party.party.group.url.hint" />
                    </div>
                </div>
            </div>
            <div style="clear: both;"></div>
        </div>
    </div>

    <div style="clear:both"></div>
    <div class="popup_button_div">
        <input type="button" value=" Cancel " class="input_button_style" onclick="window.location = '${base}/data/showSearchParty.jspx?searchCnOrEmail=${searchCnOrEmail}';"/> &nbsp;&nbsp; <input
            type="submit" name="options" value=" Next " class="input_button_style"/>
    </div>
</@s.form>
</div>
</body>
</html>