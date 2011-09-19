<#assign s=JspTaglibs["/WEB-INF/struts-tags.tld"] />
 <#assign sj=JspTaglibs["/WEB-INF/struts-jquery-tags.tld"] />
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title><@s.property value="pageTitle" /></title>
<#include "../template/jquery_header.ftl"/>
<#include "../template/googlemap_header.ftl"/>
</head>
<body>
<!-- Navigation Section including sub nav menu -->
<#include "../template/nav_section.ftl" />
<#include "../template/action_title.ftl" />
  
<div class="main_body_container">
<div class="main_big_border">
	<div class="left_container_panel">
		<br/>
		<#include "../template/action_errors.ftl" />	 
		<div class="left_middle_panel">
			<div class="none_border_block"></div>
			<div class="single_border_block">
				<@s.form action="editCollection.jspx" namespace="/data" method="post">
					<@s.hidden name="collection.id" />
					<@s.hidden name="collection.owner.id" />
					<@s.hidden name="colNameBeforeUpdate" />
					<@s.hidden name="viewType" />
					<table width="100%" class="collection_tab">
			 			<tr>
			 				<td align="left">
			 					<@s.text name="collection.name" />:
			 					<div class="name_comment">* (<@s.text name="collection.name.hint" />)</div>
			 				</td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left"><@s.textfield name="collection.name" cssClass="input_field" /> </td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
			 					<@s.text name="collection.temporal.from" />:
			 					<div class="name_comment">* (<@s.text name="collection.start.date.hint" />)</div>
			 				</td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
								 <@sj.datepicker name="collection.dateFrom" id="startdate" displayFormat="yy-mm-dd"  buttonImageOnly="true" />
							</td>
							<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
			 					<@s.text name="collection.temporal.to" />:
			 					<div class="name_comment">* (<@s.text name="collection.end.date.hint" />)</div>
			 				</td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
								 <@sj.datepicker name="collection.dateTo" id="enddate" displayFormat="yy-mm-dd"  buttonImageOnly="true" />
								 <br/>
							</td>
							<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
			 					<@s.text name="collection.desc" />:
			 					<div class="name_comment">* (<@s.text name="collection.desc.hint" />)</div>
			 				</td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
								 <@s.textarea  name="collection.description" cssStyle="width: 560px; height: 190px;" cssClass="input_textarea" />
								 <br/>
							</td>
							<td></td>
			 			</tr>
			 			 
			 			<tr>
			 				<td align="left">
			 					<br/>
			 					<@s.text name="collection.spatial.coverage"/>:
			 					<div class="name_comment">* (<@s.text name="collection.spatial.coverage.hint" />)</div>
			 				</td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
			 					<@s.textarea  id="spatialcvg" name="collection.spatialCoverage" cssStyle="width: 200px; height: 80px;" cssClass="input_textarea" readonly ="true" />
			 				</td>
			 				<td></td>
			 			</tr>
			 			<tr>
			 				<td align="left">
			 					<div class="name_comment">Choose a method for marking spatial coverage from the options in the grey bar above the map.</div>
			 				</td>
			 				<td></td>
			 			</tr>
			 			 
			 			<tr>
			 				<td>
			 					<script type="text/javascript">mctSetMapControl("spatialcvg");</script>
							</td>
			 				<td align="left"></td>
			 			</tr>
			 			
			 			<tr>
			 				<td>&nbsp;</td>
			 				<td align="left"></td>
			 			</tr>
			 			<tr>
							<td align="center"> 
								<@s.submit value="%{getText('data.edit.button')}" cssClass="input_button_style" /> &nbsp; <@s.reset value="%{getText('reset.button')}" cssClass="input_button_style" />
							</td>
							<td align="left"></td>
						</tr>
		 			</table>
				</@s.form>
			</div>
			<div class="none_border_block"></div>
		</div>	
		<div class="none_border_space_block"></div>
		<div class="none_border_block"></div>
	</div>
	<div class="right_container_panel">
		<#include "../template/subnav_section.ftl" />
	</div>
	<br/>
	<div style="clear:both"></div>
</div>
</div>
<br/>
<br/>
<#include "../template/footer.ftl"/>
</body>
</html>