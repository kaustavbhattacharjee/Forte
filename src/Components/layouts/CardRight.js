/* eslint-disable no-useless-constructor */
/* eslint-disable no-unused-vars, array-callback-return, no-redeclare */
import React, {Component} from 'react';
import { connect } from "react-redux";
import { Card, CardGroup} from 'react-bootstrap';
import Grid from '@mui/material/Grid';
import * as $ from "jquery";
import 'bootstrap/dist/css/bootstrap.min.css';
import MetricsChart from '../charts/MetricsChart2';
import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
//import LoadingButton from '@mui/lab/LoadingButton';
//import Button from 'react-bootstrap/Button';
//import 'bootstrap/dist/css/bootstrap.min.css';
import * as jsonCall from "../../Algorithms/JSONCall";
import NoiseAdditionOption from './NoiseAdditionOption';

export class  CardRight extends Component {
  
  constructor(props) {
    super(props);
    console.log();
    this.state = {
      metrics:[],
      metrics_unit:[],
      metrics_data:[],
      metrics_nan_percentage: [],
      mini_card_height: ((100/3) + "%"),
    }
  
}
componentDidMount() {}
componentDidUpdate() {}
shouldComponentUpdate(nextProps, nextState){
    return true
}





render(){ 
  if(this.props.url_version === "1.3"){
    var metrics = this.props.selected_variables;//["temperature", "humidity", "apparent_power"];
    var metrics_unit = [" (°F)", " (%)", " (kVA)"];
    var metrics_data = [[...this.props.temperature_df], [...this.props.humidity_df], [...this.props.apparent_power_df], [...this.props.temperature_df]];
    var metrics_nan_percentage = [Math.round(this.props.temperature_nans_percentage), Math.round(this.props.humidity_nans_percentage), Math.round(this.props.apparent_power_nans_percentage), Math.round(this.props.apparent_power_nans_percentage)];
    var mini_card_height = (metrics.length<=3)?((100/metrics.length) + "%"):((100/3) + "%");
  }
  else{
    console.log("Version loaded: ",this.props.url_version)
    var metrics = this.props.selected_variables;//["temperature", "humidity", "apparent_power"];
    //metrics = metrics.filter(m => m !== "ETR (W/m^2)"); // Removing ETR for time being
    var metrics_unit = []; //["", "", "", "", "", ""];
    var metrics_data = [];
    var metrics_nan_percentage = [];
    metrics.map(m =>{
      //console.log("CHecking: ", [...(this.props.input_variable_df)[m]])
      metrics_data.push([...(this.props.input_variable_df)[m]])
      metrics_nan_percentage.push(Math.round((this.props.nans_dict_percentage)[m]))
      metrics_unit.push((this.props.selected_variables_unit)[m])
    })
    //var metrics_data = [[...this.props.temperature_df], [...this.props.humidity_df], [...this.props.apparent_power_df], [...this.props.temperature_df]];
    //var metrics_nan_percentage = [Math.round(this.props.temperature_nans_percentage), Math.round(this.props.humidity_nans_percentage), Math.round(this.props.apparent_power_nans_percentage), Math.round(this.props.apparent_power_nans_percentage)];
    var mini_card_height = (metrics.length<=3)?((100/metrics.length) + "%"):((100/3) + "%");
  }


  return (
    <div style={{height: "90vh", overflow:"scroll"}}>
    {metrics.map((metric, metric_index) =>{
      console.log(metric, metric_index)
        return <Card key={metric_index} style={{height: mini_card_height}}>
        <Card.Header>
          <Grid container direction="row" spacing={1}>
            <Grid item xs={8} sm={8}>{metric.replaceAll("_", " ")+metrics_unit[metric_index]}   {(metrics_nan_percentage[metric_index] > 0)?<i className={"fa fa-info-circle metrics_nans_info_icon_"+metric} aria-hidden="true"></i>:null}</Grid>
            {/* <Grid item xs={1} sm={1}></Grid> */}
            <Grid item xs={4} sm={4}>
              <Grid container direction="row" spacing={5}>
                <Grid item xs={4} sm={4}>{(metrics.includes(metric))?<NoiseAdditionOption the_metric={metric} the_data={metrics_data[metric_index]}></NoiseAdditionOption>:null}</Grid>
                <Grid item xs={4} sm={4}>{(metrics.includes(metric))?<Tooltip title={(this.props.isLoadingUpdate)?"Loading":(((this.props.updated_metric[metric]).length === 0)?"Drag this chart to make changes":"Click the button to reset the changes")} placement="top" arrow><span><Button size="small"  color="secondary"  disabled={this.props.isLoadingUpdate || ((this.props.updated_metric[metric]).length === 0)}  style={{ backgroundColor: "#efefef", opacity: 1, borderRadius: 0, color: (this.props.isLoadingUpdate || ((this.props.updated_metric[metric]).length === 0))?null:"black",  marginTop: -2, textTransform: 'none' }}
                onClick={()=>{
                  this.props.set_isLoadingUpdate(true);
                  var converted_start_date = new Date(this.props.start_date_temp)
                  converted_start_date = (converted_start_date.toISOString()).replace("T", " ").replace(".000Z", "")
                  var converted_end_date = new Date(this.props.end_date_temp)
                  converted_end_date = (converted_end_date.toISOString()).replace("T", " ").replace(".000Z", "")

                  var metrics_updated ={}
                  metrics.map(em => {metrics_updated[em]=((this.props.updated_metric[em]).length===0 || em===metric)?0:1}) // capturing which metrics are updated

                  var processor = "processor_15min_ahead";
                  if(this.props.selected_model === "net load 15 min ahead"){processor = "processor_15min_ahead"}
                  else if(this.props.selected_model === "net load 24 hr ahead"){processor = "processor_24hr_ahead"}
                  

                  jsonCall.download(this.props.url + "/api/v@"+this.props.url_version+"/processor", {start_date: converted_start_date, end_date: converted_end_date, solar_penetration:this.props.solar_penetration_temp, metrics_updated:metrics_updated, updated_metric:this.props.updated_metric}).then(res =>{
                    console.log(res);
                    this.props.set_net_load_df_old(this.props.net_load_df);
                    this.props.set_conf_95_df_old(this.props.conf_95_df); //Saving the older values
                    this.props.set_net_load_df(res["net_load_df"]);
                    this.props.set_conf_95_df(res["conf_95_df"]);
                    this.props.set_temperature_df(res["temperature_df"]);
                    this.props.set_humidity_df(res["humidity_df"]);
                    this.props.set_apparent_power_df(res["apparent_power_df"]);
                    this.props.set_temperature_nans_percentage(res["temperature_nans_percentage"]);
                    this.props.set_humidity_nans_percentage(res["humidity_nans_percentage"]);
                    this.props.set_apparent_power_nans_percentage(res["apparent_power_nans_percentage"]);
                    var updated_metric =this.props.updated_metric;
                    updated_metric[metric] = []; // resetting the metric that is being reset
                    this.props.set_updated_metric(updated_metric);
                    this.props.set_noise_temperature_temp(-1);
                    this.props.set_mae(res["7. MAE"]);
                    this.props.set_mape(res["8. MAPE"]);
                    this.props.set_isLoadingUpdate(false);
                    
                    })
                }}>{this.props.isLoadingUpdate ? 'Loading...' : 'Reset'}</Button></span></Tooltip>:null}</Grid>


                <Grid item xs={4} sm={4}>{(metrics.includes(metric))?<Tooltip title={(this.props.isLoadingUpdate)?"Loading":(((this.props.updated_metric[metric]).length === 0)?"Drag this chart to make changes":"Click the button to see the changes")} placement="top" arrow><span><Button size="small"  color="secondary"  disabled={this.props.isLoadingUpdate || ((this.props.updated_metric[metric]).length === 0)}  style={{ backgroundColor: "#efefef", opacity: 1, borderRadius: 0, color: (this.props.isLoadingUpdate || ((this.props.updated_metric[metric]).length === 0))?null:"black",  marginTop: -2, textTransform: 'none' }}
                onClick={()=>{
                  this.props.set_isLoadingUpdate(true);
                  var converted_start_date = new Date(this.props.start_date_temp)
                  converted_start_date = (converted_start_date.toISOString()).replace("T", " ").replace(".000Z", "")
                  var converted_end_date = new Date(this.props.end_date_temp)
                  converted_end_date = (converted_end_date.toISOString()).replace("T", " ").replace(".000Z", "")
                  
                  var metrics_updated ={}
                  metrics.map(em => {metrics_updated[em]=((this.props.updated_metric[em]).length>0)?1:0}) // capturing which metrics are updated
                  
                  var processor = "processor_15min_ahead";
                  if(this.props.selected_model === "net load 15 min ahead"){processor = "processor_15min_ahead"}
                  else if(this.props.selected_model === "net load 24 hr ahead"){processor = "processor_24hr_ahead"}

                  jsonCall.download(this.props.url + "/api/v@"+this.props.url_version+"/processor", {start_date: converted_start_date, end_date: converted_end_date, solar_penetration:this.props.solar_penetration_temp, metrics_updated:metrics_updated, updated_metric: this.props.updated_metric}).then(res =>{
                    console.log(res);
                    this.props.set_net_load_df_old(this.props.net_load_df);
                    this.props.set_conf_95_df_old(this.props.conf_95_df); //Saving the older values
                    this.props.set_net_load_df(res["net_load_df"]);
                    this.props.set_conf_95_df(res["conf_95_df"]);
                    this.props.set_temperature_df(res["temperature_df"]);
                    this.props.set_humidity_df(res["humidity_df"]);
                    this.props.set_apparent_power_df(res["apparent_power_df"]);
                    this.props.set_temperature_nans_percentage(res["temperature_nans_percentage"]);
                    this.props.set_humidity_nans_percentage(res["humidity_nans_percentage"]);
                    this.props.set_apparent_power_nans_percentage(res["apparent_power_nans_percentage"]);
                    this.props.set_mae(res["7. MAE"]);
                    this.props.set_mape(res["8. MAPE"]);
                    this.props.set_isLoadingUpdate(false);
                    
                    })
                }}>{this.props.isLoadingUpdate ? 'Loading...' : 'Update'}</Button></span></Tooltip>:null}</Grid>
              </Grid>
            </Grid>  
          </Grid>
        </Card.Header>
        <Card.Body style={{opacity:(this.props.isLoadingUpdate)?0.4:1}} >
            {(metrics.includes(metric) & (this.props.net_load_df).length >0 )?<MetricsChart the_metric={metric} the_data={metrics_data[metric_index]} the_nans_percentage={metrics_nan_percentage[metric_index]} the_noise_control={this.props.noise_control} ></MetricsChart>:null}
        </Card.Body>
        </Card>
    })}    
    
    </div>  

    
  );  

 } //return ends
}

const maptstateToprop = (state) => {
  return {
      blank_placeholder: state.blank_placeholder,
      url: state.url,
      url_version: state.url_version,
      isLoadingUpdate: state.isLoadingUpdate,
      start_date: state.start_date,
      end_date: state.end_date,
      start_date_temp: state.start_date_temp,
      end_date_temp: state.end_date_temp,
      solar_penetration_temp: state.solar_penetration_temp,
      net_load_df: state.net_load_df,
      conf_95_df: state.conf_95_df,
      temperature_df: state.temperature_df,
      humidity_df: state.humidity_df,
      apparent_power_df : state.apparent_power_df,
      input_variable_df: state.input_variable_df,
      temperature_nans_percentage: state.temperature_nans_percentage,
      humidity_nans_percentage: state.humidity_nans_percentage,
      apparent_power_nans_percentage: state.apparent_power_nans_percentage,
      nans_dict_percentage: state.nans_dict_percentage,
      updated_temperature: state.updated_temperature,
      updated_humidity: state.updated_humidity,
      updated_apparent_power: state.updated_apparent_power, // need to keep this to trigger an update
      updated_metric: state.updated_metric,
      noise_control: state.noise_control,
      selected_variables: state.selected_variables,
      selected_variables_unit: state.selected_variables_unit,
      selected_model: state.selected_model,
  }
}
const mapdispatchToprop = (dispatch) => {
  return {
      set_blank_placeholder: (val) => dispatch({ type: "blank_placeholder", value: val }),
      set_isLoadingUpdate: (val) => dispatch({ type: "isLoadingUpdate", value: val }),
      set_start_date: (val) => dispatch({ type: "start_date", value: val }),
      set_end_date: (val) => dispatch({ type: "end_date", value: val }),
      set_net_load_df: (val) => dispatch({ type: "net_load_df", value: val}),
      set_conf_95_df: (val) => dispatch({ type: "conf_95_df", value: val}),
      set_net_load_df_old: (val) => dispatch({ type: "net_load_df_old", value: val}),
      set_conf_95_df_old: (val) => dispatch({ type: "conf_95_df_old", value: val}),
      set_temperature_df: (val) => dispatch({ type: "temperature_df", value: val}),
      set_humidity_df: (val) => dispatch({ type: "humidity_df", value: val}),
      set_apparent_power_df: (val) => dispatch({ type: "apparent_power_df", value: val}),
      set_temperature_nans_percentage: (val) => dispatch({ type: "temperature_nans_percentage", value: val}),
      set_humidity_nans_percentage: (val) => dispatch({ type: "humidity_nans_percentage", value: val}),
      set_apparent_power_nans_percentage: (val) => dispatch({ type: "apparent_power_nans_percentage", value: val}),
      set_solar_penetration: (val) => dispatch({ type: "solar_penetration", value: val}),
      set_updated_metric: (val) => dispatch({ type: "updated_metric", value: val }),
      set_noise_temperature_temp: (val) => dispatch({ type: "noise_temperature_temp", value: val }),
      set_mae: (val) => dispatch({ type: "mae", value: val}),
      set_mape: (val) => dispatch({ type: "mape", value: val}),
  }
}

export default connect(maptstateToprop, mapdispatchToprop)(CardRight);