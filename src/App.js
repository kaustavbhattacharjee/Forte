/* eslint-disable no-unused-vars, array-callback-return, no-redeclare */
import React, {Component} from 'react';
import {connect} from "react-redux";
import Grid from '@mui/material/Grid';
import AppBar from './Components/appbar/AppBar';
import * as d3 from "d3";
//import logo from './logo.svg';
import './App.css';
import CardLeft from './Components/layouts/CardLeft';
import CardRight from './Components/layouts/CardRight';
import moment from 'moment-timezone';
import * as jsonCall from "./Algorithms/JSONCall";
import './App.css'



class App extends Component{
  constructor(props){
    super(props);
    moment.tz.setDefault('UTC');
    console.log();
  }

  componentDidMount(){
    this.props.set_isLoadingUpdate(true); 
    var converted_start_date = new Date(this.props.start_date)
    converted_start_date = (converted_start_date.toISOString()).replace("T", " ").replace(".000Z", "")
    var converted_end_date = new Date(this.props.end_date)
    converted_end_date = (converted_end_date.toISOString()).replace("T", " ").replace(".000Z", "")
    console.log("Version loaded: ",this.props.url_version)

    if(this.props.url_version === "1.3"){
      var metrics_updated ={}
      var metrics = ["temperature", "humidity", "apparent_power"]
      var processor = "processor_15min_ahead";
      if(this.props.selected_model === "net load 15 min ahead"){processor = "processor_15min_ahead"}
      else if(this.props.selected_model === "net load 24 hr ahead"){processor = "processor_24hr_ahead"}
      console.log(this.props.url + "/api/v@"+this.props.url_version+"/processor");
      metrics.map(em => {metrics_updated[em]=0}) // none of the metrics should be updated
      jsonCall.download(this.props.url + "/api/v@"+this.props.url_version+"/processor", {start_date: converted_start_date, end_date: converted_end_date, solar_penetration:this.props.solar_penetration, temperature_updated:0,humidity_updated:0, apparent_power_updated:0, metrics_updated:metrics_updated, updated_metric:this.props.updated_metric, selected_model:this.props.selected_model}).then(res =>{
        console.log(res);
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
        this.props.set_mean_ape(res["8a. Mean APE"]);
        this.props.set_median_ape(res["8b. Median APE"]);
        this.props.set_mode_ape(res["8c. Mode APE"]);
        this.props.set_isLoadingUpdate(false);
        
        })
    
    }
    else{
      console.log("Came here in 1.4")
      var metrics_updated ={}
      var metrics = ["SZA", "AZM", "ETR", "GHI", "Wind_Speed", "Temperature"]
      
      metrics.map(em => {metrics_updated[em]=0}) // none of the metrics should be updated
      jsonCall.download(this.props.url + "/api/v@"+this.props.url_version+"/processor", {start_date: converted_start_date, end_date: converted_end_date, solar_penetration:this.props.solar_penetration, temperature_updated:0,humidity_updated:0, apparent_power_updated:0, metrics_updated:metrics_updated, updated_metric:this.props.updated_metric, selected_model:this.props.selected_model}).then(res =>{
        console.log(res);
        this.props.set_net_load_df(res["net_load_df"]);
        this.props.set_conf_95_df(res["conf_95_df"]);
        // this.props.set_temperature_df(res["temperature_df"]);
        // this.props.set_humidity_df(res["humidity_df"]);
        // this.props.set_apparent_power_df(res["apparent_power_df"]);
        console.log("CHecking -1:", res["input_variable_df"])
        this.props.set_input_variable_df(res["input_variable_df"]);
        // this.props.set_temperature_nans_percentage(res["temperature_nans_percentage"]);
        // this.props.set_humidity_nans_percentage(res["humidity_nans_percentage"]);
        // this.props.set_apparent_power_nans_percentage(res["apparent_power_nans_percentage"]);
        this.props.set_nans_dict_percentage(res["nans_dict_percentage"]);
        this.props.set_mae(res["7. MAE"]);
        this.props.set_mape(res["8. MAPE"]);
        this.props.set_mean_ape(res["8a. Mean APE"]);
        this.props.set_median_ape(res["8b. Median APE"]);
        this.props.set_mode_ape(res["8c. Mode APE"]);
        this.props.set_isLoadingUpdate(false);
        
        })
      
    }
    
  }

  componentDidUpdate(){

  }

  render(){

    return(
      <Grid container spacing={0} >
          <Grid item xs={12}><AppBar style={{height:"5vh"}}></AppBar></Grid>
          <Grid item xs={12}>
          {/* <Grid container style={{opacity:(this.props.isLoadingUpdate)?0.4:1}}> */}
          <Grid container>
          <Grid item xs={12} lg={6}><CardLeft></CardLeft></Grid>
          {/* {(this.props.input_variable_df | this.props.url_version === "1.3")?<Grid item xs={12} lg={6}><CardRight></CardRight></Grid>:null} */}
          {(this.props.url_version === "1.3")?<Grid item xs={12} lg={6}><CardRight></CardRight></Grid>:((this.props.input_variable_df)?<Grid item xs={12} lg={6}><CardRight></CardRight></Grid>:null)}
          {/* <Grid item xs={12} lg={6}><CardRight></CardRight></Grid> */}
          </Grid>
        </Grid>
        </Grid>
    )
  }
}

const mapStateToProp = (state) => {
  return {
    blank_placeholder: state.blank_placeholder,
    url: state.url,
    url_version: state.url_version,
    isLoadingUpdate: state.isLoadingUpdate,
    actual_net_load: state.actual_net_load,
    predicted_net_load: state.predicted_net_load,
    apparent_power: state.apparent_power,
    humidity: state.humidity,
    temperature: state.temperature,
    solar_penetration: state.solar_penetration,
    start_date: state.start_date,
    end_date: state.end_date,
    updated_metric: state.updated_metric,
    selected_model: state.selected_model,
    input_variable_df: state.input_variable_df,

  }
}

const mapDispatchToProp = (dispatch) => {
  return{
    set_blank_placeholder: (val) => dispatch({ type: "blank_placeholder", value: val}),
    set_isLoadingUpdate: (val) => dispatch({ type: "isLoadingUpdate", value: val }),
    set_actual_net_load: (val) => dispatch({ type: "actual_net_load", value: val}),
    set_predicted_net_load: (val) => dispatch({ type: "predicted_net_load", value: val}),
    set_apparent_power: (val) => dispatch({ type: "apparent_power", value: val}),
    set_humidity: (val) => dispatch({ type: "humidity", value: val}),
    set_temperature: (val) => dispatch({ type: "temperature", value: val}),
    set_net_load_df: (val) => dispatch({ type: "net_load_df", value: val}),
    set_conf_95_df: (val) => dispatch({ type: "conf_95_df", value: val}),
    set_temperature_df: (val) => dispatch({ type: "temperature_df", value: val}),
    set_humidity_df: (val) => dispatch({ type: "humidity_df", value: val}),
    set_apparent_power_df: (val) => dispatch({ type: "apparent_power_df", value: val}),
    set_input_variable_df: (val) => dispatch({ type: "input_variable_df", value: val}),
    set_temperature_nans_percentage: (val) => dispatch({ type: "temperature_nans_percentage", value: val}),
    set_humidity_nans_percentage: (val) => dispatch({ type: "humidity_nans_percentage", value: val}),
    set_apparent_power_nans_percentage: (val) => dispatch({ type: "apparent_power_nans_percentage", value: val}),
    set_nans_dict_percentage: (val) => dispatch({ type: "nans_dict_percentage", value: val}),
    set_mae: (val) => dispatch({ type: "mae", value: val}),
    set_mape: (val) => dispatch({ type: "mape", value: val}),
    set_mean_ape: (val) => dispatch({ type: "mean_ape", value: val}),
    set_median_ape: (val) => dispatch({ type: "median_ape", value: val}),
    set_mode_ape: (val) => dispatch({ type: "mode_ape", value: val}),
  }
}
export default connect(mapStateToProp,mapDispatchToProp)(App);