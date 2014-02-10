<#assign s=JspTaglibs["/WEB-INF/struts-tags.tld"] />
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns="http://www.w3.org/1999/html">
<head>
    <title><@s.property value="pageTitle" /></title>
<#include "../template/jquery_header.ftl"/>
    <script type="text/javascript">
        $(function () {
            $.superbox.settings = {
                closeTxt:"Close",
                loadTxt:"Loading...",
                nextTxt:"Next",
                prevTxt:"Previous"
            };
            $.superbox();
        });
    </script>
</head>
<body>
<!-- Navigation Section including sub nav menu -->
<#include "../template/nav_section.ftl" />
<!-- Navigation Title -->
<#include "../template/action_title.ftl" />
<!-- End of Navigation Title -->

<div class="main_body_container">
    <div class="display_middel_div">
        <div class="left_display_div">
        <#include "../template/action_errors.ftl" />
            <div style="clear:both"></div>
            <div class="left_display_inner">
            <@s.form action="mdRegister.jspx" namespace="/data" method="post" id="mdRegForm">
                <@s.hidden name="collection.id" id="col"/>
                <@s.hidden name="collection.name" id="coname"/>
                <@s.hidden name="collection.description" id="desc"/>
                <@s.hidden name="collection.owner.displayName" id="codisplayname" />
                <@s.hidden name="collection.owner.id" id="colowner" />
                <@s.hidden name="collection.createdTime" />
                <@s.hidden name="collection.modifiedTime" />
                <@s.hidden name="collection.modifiedByUser.displayName" />
                <@s.hidden name="viewType" id="viewtype"/>
                <@s.hidden name="collection.funded" id="funded"/>
                <div class="content_none_border_div">
                    <div class="content_title">Instructions to publish metadata on external data portals</div>
                </div>
                <div class="data_display_div">
                    <div class="md_publish_spec">
                        <p>
                           <span class="span_inline2">The following mandatory steps will enable you to successfully publish your collection metadata to various external data portals, such as <a href="http://www.tern.org.au" target="_blank">TERN</a>, <a href="http://researchdata.ands.org.au/" target="_blank">RDA</a>, etc.</span>
                        </p>

                        <p>
                            <span class="md_step">Step 1:</span> Search for researchers associated with this collection in this step. To do this, click on the <b>Add Researcher</b> button. If a researcher name isn't found in the
                            database, you will be asked to create their profile. Once created, the new researcher profile can be associated to this collection. At least one researcher must be
                            associated to a collection.
                        </p>

                        <p>
                            <span class="md_step">Step 2:</span> Review Fair Use Policy.
                        </p>

                        <p>
                            <span class="md_step">Step 3:</span> Review the Terms and Conditions, to comply with the publication of your collection and its associated metadata on various external data portals. Click on <b>I accept, Publish</b> button to complete the registration of your data.
                        </p>

                        <p>
                            <span class="span_inline2">It may take up to a week for the metadata to be published on the portals.</span>
                        </p>
                    </div>
                </div>
                <div class="content_none_border_div">
                    <div class="content_title">Step 1: Associated Researcher(s)</div>
                </div>
                <div class="content_none_border_div">
                    <div class="metada_reg_display_div">
                        <div class="metadata_spec">
                            Please select the associated researcher(s)
                        </div>
                        <div class="metadata_act_link">
                            <a href="${base}/data/showSearchParty.jspx" title="Adding an associated researcher" rel="superbox[iframe.addparty][600x500]">Add Researcher</a>
                        </div>
                        <div style="clear: both;"></div>
                    </div>
                </div>

                <div class="register_md_div">
                    <table class="display_data_tab2" id="ands_party_div">
                        <tbody>
                            <@s.if test="%{partyList != null && partyList.size > 0}">
                                <@s.iterator status="ptState" value="partyList" id="party" >
                                <tr>
                                    <td width="50" align="center">
                                        <@s.checkbox name="partyList[${ptState.index}].selected"  cssClass="check_box" />
                                    </td>
                                    <td>
                                        <@s.property value="#party.personTitle" /> <@s.property value="#party.personGivenName" /> <@s.property value="#party.personFamilyName" />
                                        ( <@s.property value="#party.groupName" /> - <@s.property value="#party.email" /> )
                                        <@s.hidden name="partyList[${ptState.index}].partyKey" />
                                        <@s.hidden name="partyList[${ptState.index}].personTitle" />
                                        <@s.hidden name="partyList[${ptState.index}].personGivenName" />
                                        <@s.hidden name="partyList[${ptState.index}].personFamilyName" />
                                        <@s.hidden name="partyList[${ptState.index}].email" />
                                        <@s.hidden name="partyList[${ptState.index}].address" />
                                        <@s.hidden name="partyList[${ptState.index}].url" />
                                        <@s.hidden name="partyList[${ptState.index}].identifierType"  />
                                        <@s.hidden name="partyList[${ptState.index}].identifierValue" />
                                        <@s.hidden name="partyList[${ptState.index}].originateSourceType" />
                                        <@s.hidden name="partyList[${ptState.index}].originateSourceValue" />
                                        <@s.hidden name="partyList[${ptState.index}].groupKey" />
                                        <@s.hidden name="partyList[${ptState.index}].groupName" />
                                        <@s.hidden name="partyList[${ptState.index}].fromRm" />
                                    </td>
                                </tr>
                                </@s.iterator>
                            </@s.if>
                            <@s.else>
                            <div class="none_party_div">
                                The associated researcher(s) not found, please select an associated researcher
                            </div>
                            </@s.else>
                        <tbody>
                    </table>
                </div>
                <div class="content_none_border_div">
                    <div class="content_title">Step 2: Review <a href="http://eddy.googlecode.com/files/OzFluxFairUseAndAcknowledgement.pdf" target="_blank">Fair Use Policy </a></div>
                </div>
                <div class="blank_separator"></div>
                <div class="content_none_border_div">
                    <div class="content_title">Step 3: Terms and Conditions</div>
                </div>

                <div class="register_md_div">
                    <div class="publish_term_conditions">
                        <p>
                            You are about to publish or register the above research work outside Monash University to be available to the
                            general public via Internet sites that can harvest this information. Sites include but are not limited to:
                            Research Data Australia and search engines.
                        </p>

                        <p>
                            Before you proceed, please ensure you have selected a license to associate with your research data and
                            work.
                        </p>

                        <p>
                            By using this system to publish or register your research work you are continuing to agree to adhere to the
                            <a href="http://eddy.googlecode.com/files/OzFluxTermsAndConditions.pdf" target="_blank">Terms and Conditions</a>.
                            Please read these Terms and Conditions carefully before publishing.
                        </p>
                    </div>
                </div>

                <div class="content_none_border_div">
                    <div class="metada_reg_display_div">
                        <div class="metadata_spec">
                            &nbsp;
                        </div>
                        <div class="metadata_act_link">
                            <@s.submit value="I accept. Publish"  name="register" cssClass="input_button_simple" id="wait_modal" />
                        </div>
                        <div id='mask'></div>
                        <div id='modal_window'>
                            Calling Metadata Publishing Service, please wait ... <img src="${base}/images/wait_loader.gif" class="loading_image">
                        </div>
                        <div style="clear: both;"></div>
                    </div>
                </div>
            </@s.form>
            </div>
        </div>
        <!-- right panel -->
        <div class="right_display_div">
        <@s.if test="%{#session.authentication_flag =='authenticated'}">
                <#include "../template/sub_nav.ftl" />
            </@s.if>
        </div>
    </div>
    <div style="clear:both"></div>
</div>
<#include "../template/footer.ftl"/>
</body>
</html>
