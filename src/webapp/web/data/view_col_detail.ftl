<#assign s=JspTaglibs["/WEB-INF/struts-tags.tld"] />
<#assign sj=JspTaglibs["/WEB-INF/struts-jquery-tags.tld"] />
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title><@s.property value="pageTitle" /></title>
<#include "../template/jquery_header.ftl"/>
    <script type="text/javascript">
        function doAfterImport(success) {
            if (success) {
            <@s.if test = "%{navigationBar.secondNavLink != null}">
                setTimeout('window.location.href = "${base}/${navigationBar.secondNavLink}"', 3500);
            </@s.if>
            }
        }
        ;
        $(function () {
            $.superbox.settings = {
                closeTxt:"Close",
                loadTxt:"Loading...",
                nextTxt:"Next",
                prevTxt:"Previous"
            };
            $.superbox();
        });

        $(document).ready(function () {
            var raEnabledCheck = $('#ra_enabled');
            var im_ra_setting = $(".im_ra_section");
            if (raEnabledCheck.is(":checked")) {
                im_ra_setting.show();
            } else {
                im_ra_setting.hide();
            }
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

<@s.if test="%{collectionError == false }">
    <@s.if test="%{actionSuccessMsg != null}">
    <div class="content_none_border_div">
        <div class="none_border_block">
            <#include "../template/action_success_msg.ftl"/>
        </div>
    </div>
    </@s.if>

<!-- End of file importing message block -->

<div class="data_display_div">
    <div class="data_title">
        <@s.property value="collection.name"/>
    </div>
    <div class="data_desc_div">
        <@s.property  value="collection.description" escape=false />
    </div>
    <div class="data_other_info">
        <span class="span_inline1">
            Created by <@s.property value="collection.owner.displayName" />,
        </span>
        <span class="span_inline1">
            Creation date: <@s.date name="collection.createdTime" format="yyyy-MM-dd hh:mm" />,
        </span>
       <span class="span_inline1">
            Modified by <@s.property value="collection.modifiedByUser.displayName" />,
        </span>
        <span class="span_inline1">
            Modified date: <@s.date name="collection.modifiedTime" format="yyyy-MM-dd hh:mm" />
        </span>
    </div>
    <div class="input_field_row">
        <div class="status_field_name_div">Temporal Coverage:</div>
        <div class="status_field_value_div">
            <@s.date name="collection.dateFrom" format="yyyy-MM-dd" />&nbsp;-&nbsp;<@s.date name="collection.dateTo" format="yyyy-MM-dd" />
        </div>
    </div>

    <div class="input_field_row">
        <div class="status_field_name_div">Metadata Published:</div>
        <div class="status_field_value_div">
            <@s.if test = "%{collection.published == true }">
                Yes
            </@s.if>
            <@s.else>
                No
            </@s.else>
        </div>
    </div>
    <@s.if test="%{collection.funded == true}">
        <div class="data_tern_div">
            [ <a href="http://www.tern.org.au" target="_blank">TERN-Funded</a> ]
        </div>
    </@s.if>

    <div class="data_action_link2">

        <@s.if test="%{#session.authentication_flag =='authenticated' && collection.owner.id != user.id}">
            <a href="mailto:${user.email}">
                Contact Owner
            </a>
        </@s.if>
        <@s.if test="%{permissionBean.updateAllowed == true}">
            <a href="${base}/${showColEditLink}?collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}">
                Edit
            </a>
        </@s.if>
        <@s.if test="%{permissionBean.deleteAllowed}">
            <div class="msg_content">All data will be removed from the repository permanently!<p>Are you sure to delet
                this collection?</p></div>
            <div id='confirm_dialog'>
                <div class='header'><span>Deleting Collection Confirm</span></div>
                <div class='message'></div>
                <div class='buttons'>
                    <div class='no simplemodal-close'>No</div>
                    <div class='yes'>Yes</div>
                </div>
            </div>
            <a href="${base}/${deleteColLink}?collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}"
               class="confirm">
                Delete
            </a>
        </@s.if>
        <@s.if test="%{permissionBean.acAllowed}">
            <a href="${base}/${permissionLink}?collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}">
                Permissions
            </a>
        </@s.if>
        <@s.if test="%{permissionBean.mdRegAllowed}">
            <a href="${base}/${andsMdRegLink}?collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}"
               title="Public registration of the metadata associated with this collection with the Research Data Australia website">
                <@s.text name="ands.md.registration.title" />
            </a>
        </@s.if>
    </div>
    <div style="clear: both;"></div>
</div>
    <@s.if test="%{collection.published == true}">
    <div class="data_display_div">
        <div class="citation_title">Citation Information</div>
        <div class="citation_hints">If you make use of this collection in your research, please cite:</div>
        <div class="citation_contents_div">
            <@s.property value='collection.owner.firstName' />  <@s.property value='collection.owner.lastName' /> (<@s.date name="collection.createdTime" format="yyyy" />
            ) <@s.property value="collection.name"/>
            <@s.property value="publisher"/>
            <@s.if test = '%{collection.persistIdentifier.indexOf("/") != -1}'>
                hdl: <@s.property value="collection.persistIdentifier"/>
            </@s.if>
            <@s.else>
                local: <@s.property value="collection.persistIdentifier"/>
            </@s.else>
        </div>
    </div>
    </@s.if>

<!-- import the file -->
    <@s.if test="%{permissionBean.importAllowed}">
    <div class="blank_separator"></div>
    <div class="content_none_border_div">
        <div class="content_title">File Import</div>
    </div>

    <!-- File importing message block -->
    <div class="content_none_border_div">
        <div class="file_success_msg_div">
            <p id="file_success_msg">Some text</p>
        </div>

        <div class="file_error_msg_div">
            <div class="file_error_msg_item_div">
            </div>
        </div>
    </div>

    <!-- file uploading progress messages -->
    <div class="content_none_border_div">
        <div class="file_uploading_div">
            <div id="ajaxfileupload">
                <div id="fileuploadProgress">
                    <div id="uploadFilename">Initialising, please wait.....</div>
                    <div id="progress-bar">
                        <div id="progress-bgrd"></div>
                        <div id="progress-text"></div>
                    </div>
                    <br/>
                </div>
                <span id="message"></span>
            </div>
        </div>
    </div>


    <!-- upload file -->
    <div class="data_display_div">
        <div id="fileuploadForm">
            <@s.form id="ajaxFileUploadForm" onsubmit="return false" action="importFile.jspx" namespace="/data" method="post" enctype="multipart/form-data" >
                <@s.hidden name="collection.id" id="col"/>
                <@s.hidden name="collection.owner.id" id="colowner" />
                <@s.hidden name="viewType" id="viewtype"/>

                <div class="input_field_row">
                    <div class="input_field_title">
                        Please select a file:
                    </div>
                    <div class="input_field_value_section">
                        <@s.file name="upload" id="upload" cssClass="input_file" />
                    </div>
                </div>
                <div style="clear: both;"></div>

                <div class="input_field_row">
                    <div class="input_field_title">
                        Extract the Metadata:
                    </div>
                    <div class="input_field_value_section">
                        <@s.checkbox name="extractable"  id="extract" value="true" cssClass="check_box" />
                    </div>
                </div>
                <div style="clear: both;"></div>
                <@s.if test="%{permissionBean.racAllowed}">
                    <div class="input_field_row">
                        <div class="input_field_title">
                            Restricted Access Enabled:
                        </div>
                        <div class="input_field_value_section">
                            <@s.checkbox name="raEnabled"  id="ra_enabled" cssClass="check_box" />
                        </div>
                    </div>
                    <div style="clear: both;"></div>

                    <div class="im_ra_section">
                        <div class="im_ra_label">Restricted Access Settings</div>
                        <div class="im_ra_input_panel">
                            <div class="blank_separator"></div>
                            <div class="ra_field_title">
                                <span class="ra_span">Start Date</span>: &nbsp;&nbsp; <@s.date name="restrictAccess.startDate" format="yyyy-MM-dd" />
                            </div>
                            <div class="ra_field_value_section">
                                <span class="ra_span">End Date</span>: &nbsp;&nbsp; <@sj.datepicker name="restrictAccess.endDate" id="raEndTime" displayFormat="yy-mm-dd"  buttonImageOnly="true" />
                            </div>
                            <div class="blank_separator"></div>
                            <div class="ra_comments">
                                (The start date is always today's date. The end data can be between 30 days from today and up to 18 months in the future.)
                            </div>
                        </div>
                    </div>
                </@s.if>
                <div class="blank_separator"></div>
                <div class="input_field_row">
                    <div class="input_field_title">
                        &nbsp;
                    </div>
                    <div class="input_field_value_section">
                        <@s.submit value="Import" id="fileUpload" name="fileUpload" onclick="merc.FileUpload.initialize(doAfterImport);" cssClass="input_button_style"/>
                    </div>
                </div>
            </@s.form>
        </div>
    </div>
    </@s.if>
<!-- end of importing file -->
<div class="none_border_block">
            <span class="name_title">
                 A total of <span class="span_number">
                <@s.if test = "%{raDatasets != null}"><@s.property value="raDatasets.size" /></@s.if>
                <@s.else>0</@s.else>
            </span> data file(s) in this collection
            </span>
</div>
    <@s.if test="%{raDatasets.size() > 0}">

        <@s.iterator status="dsState" value="raDatasets" id="raDs">
        <div class="dataset_info" id="ds_${dsState.index}">
            <div class="ds_file_level">
                <div class="ds_field_row">
                    <div class="ds_field_title">File Name:</div>
                    <div class="ds_field_value_section"><@s.property value="#raDs.dataset.name" /></div>
                </div>
                <div style="clear: both;"></div>
                <div class="ds_field_row">
                    <div class="ds_field_title">Site Name:</div>
                    <div class="ds_field_value_section"><@s.property value="#raDs.dataset.siteName" /></div>
                </div>
                <div style="clear: both;"></div>
                <div class="ds_field_row">
                    <div class="ds_field_title">Processing Level:</div>
                    <div class="ds_field_value_section"><@s.property value="#raDs.dataset.netCDFLevel" /></div>
                </div>
                <div style="clear: both;"></div>
            </div>
            <div class="ds_ra_act_level">
                <div class="ds_ra_info">
                    <div class="ra_info_spec">
                        <@s.if test="%{#raDs.raEnabled == false}">
                            <a href="${base}/site/licenceinfo.jspx" target="_blank">
                                <div class="info_hint">&nbsp;</div>
                            </a><span id="ra_info_spec_${dsState.index}">Access to this file is not restricted.</span>
                        </@s.if>
                        <@s.else>
                            <@s.if test="%{#raDs.raActive}">
                                <a href="${base}/site/licenceinfo.jspx" target="_blank">
                                    <div class="info_hint">&nbsp;</div>
                                </a><span id="ra_info_spec_${dsState.index}">Access to this file is restricted until <@s.date name="#raDs.ra.endDate" format="yyyy-MM-dd" />.</span>
                            </@s.if>
                            <@s.else>
                                <a href="${base}/site/licenceinfo.jspx" target="_blank">
                                    <div class="info_hint">&nbsp;</div>
                                </a><span id="ra_info_spec_${dsState.index}">Access to this file is no longer restricted, as the restriction period has expired.</span>
                            </@s.else>
                        </@s.else>
                    </div>
                    <@s.if test="%{permissionBean.racAllowed}">
                        <@s.if test="%{#raDs.raActive || #raDs.raEnabled == false}">
                            <div class="ra_control1" id="${dsState.index?c}" title="manage restricted access"></div>
                        </@s.if>
                    </@s.if>
                </div>

                <div class="ds_act_info">
                    <div class="ds_act_link">
                        <@s.if test="%{permissionBean.viewAllowed}">
                            <@s.if test="%{#raDs.dataset.extracted}">
                                <a href="${base}/${viewDatasetLink}?dataset.id=<@s.property value='#raDs.dataset.id' />&collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}"
                                   title="Dataset - ${raDs.dataset.name}" rel="superbox[iframe.viewmetadata][600x500]">
                                    View Metadata
                                </a>
                            </@s.if>
                        </@s.if>
                        <@s.if test="%{#raDs.raActive}">
                            <@s.if test="%{permissionBean.exportAllowed}">
                                <a href="${base}/${downloadDatasetLink}?dataset.id=<@s.property value='#raDs.dataset.id' />&collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}"
                                   title="Exporting Dataset - ${raDs.dataset.name}" rel="superbox[iframe.viewmetadata][600x640]">
                                    Export
                                </a>
                            </@s.if>
                        </@s.if>
                        <@s.else>
                            <a href="${base}/${downloadDatasetLink}?dataset.id=<@s.property value='#raDs.dataset.id' />&collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}"
                               title="Exporting Dataset - ${raDs.dataset.name}" rel="superbox[iframe.viewmetadata][600x640]">
                                Export
                            </a>
                        </@s.else>

                        <@s.if test="%{permissionBean.deleteAllowed}">
                            <div id='confirm_dialog'>
                                <div class="msg_content">The data will be removed from the repository permanently!
                                    <p>Are you sure to delet this dataset?</p></div>
                                <div id='confirm'>
                                    <div class='header'><span>Deleting Dataset Confirm</span></div>
                                    <div class='message'></div>
                                    <div class='buttons'>
                                        <div class='no simplemodal-close'>No</div>
                                        <div class='yes'>Yes</div>
                                    </div>
                                </div>
                            </div>
                            <a href="${base}/${deleteDatasetLink}?dataset.id=<@s.property value='#raDs.dataset.id' />&collection.id=<@s.property value='collection.id' />&collection.owner.id=<@s.property value='collection.owner.id' />&viewType=${viewType}"
                               class='confirm'>Delete</a>
                        </@s.if>
                    </div>
                </div>
                <div style="clear: both;"></div>
            </div>
        </div>
            <@s.if test="%{permissionBean.racAllowed}">
                <@s.if test="%{#raDs.raActive || #raDs.raEnabled == false}">
                    <@s.form namespace="/data" method="post" name="form_setup_ra_${dsState.index?c}">
                        <@s.hidden name="collection.id" />
                        <@s.hidden name="collection.owner.id" />
                        <@s.hidden name="viewType" />
                        <@s.hidden name="dataset.id" value="${raDs.dataset.id?c}"/>

                    <div class="dataset_ra_section" id="ds_ra_${dsState.index?c}">
                        <div class="ds_ra_lable">
                            <@s.property value="#raDs.dataset.name" /> - Restricted Access Settings
                            <div class="ds_ra_close" title="Close"></div>
                        </div>
                        <div class="ds_ra_input_panel">
                            <div class="rac_success_msg_div" id="rac_success_${dsState.index?c}">
                                <p class="rac_success_msg">Some text</p>
                            </div>

                            <div class="rac_error_msg_div" id="rac_error_${dsState.index?c}">
                                <div class="rac_error_msg_item_div">
                                    <ul>
                                        <li>Some error message</li>
                                    </ul>
                                </div>
                            </div>
                            <div class="blank_separator"></div>
                            <div class="blank_separator"></div>

                            <div class="ra_field_title">
                                <@s.hidden name="restrictAccess.startDate" value="%{#raDs.ra.startDate}" id="start_date_${dsState.index?c}"/>
                                <span class="ra_span">Start Date</span>: &nbsp;&nbsp; <@s.date name="#raDs.ra.startDate" format="yyyy-MM-dd" />
                            </div>

                            <div class="ra_field_value_section">
                                <span class="ra_span">End Date</span>:
                                &nbsp;&nbsp; <@sj.datepicker name="restrictAccess.endDate" value="%{#raDs.ra.endDate}" displayFormat="yy-mm-dd"  buttonImageOnly="true" />
                            </div>

                            <div class="ra_comments">
                                (The end data can be between 30 days from start date and up to 18 months in the future.)
                            </div>

                            <div class="ra_action_div">
                                <@s.submit value="Save" id="setup_ra" name="Save"  cssClass="input_button_style"/>
                            </div>
                        </div>
                    </div>
                    </@s.form>
                </@s.if>
            </@s.if>
        </@s.iterator>
    </@s.if>
</@s.if>
</div>
<div style="clear:both"></div>
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


