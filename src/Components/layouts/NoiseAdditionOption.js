/* eslint-disable no-unused-vars */
/* eslint-disable array-callback-return */
import React, { Component } from 'react';
import { connect } from "react-redux";
import * as $ from "jquery";
import * as d3 from "d3";
import _ from 'lodash';
import Form from 'react-bootstrap/Form';
import { styled } from '@mui/material/styles';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import NativeSelect from '@mui/material/NativeSelect';
import InputBase from '@mui/material/InputBase';

const BootstrapInput = styled(InputBase)(({ theme }) => ({
    '& .MuiInputBase-input': {
      borderRadius: 3,
      position: 'relative',
      backgroundColor: theme.palette.background.paper,
      border: '1px solid #ced4da',
      fontSize: 11,
    //   padding: '10px 26px 10px 12px',
    marginTop:'2px',
      padding: '4px 0px 2px 8px',
      transition: theme.transitions.create(['border-color', 'box-shadow']),
      // Use the system font instead of the default Roboto font.
      fontFamily: [
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'Roboto',
        '"Helvetica Neue"',
        'Arial',
        'sans-serif',
        '"Apple Color Emoji"',
        '"Segoe UI Emoji"',
        '"Segoe UI Symbol"',
      ].join(','),
      '&:focus': {
        borderRadius: 4,
        borderColor: '#80bdff',
        boxShadow: '0 0 0 0.2rem rgba(0,123,255,.25)',
      },
    },
  }));


class NoiseAdditionOption extends Component {
    constructor(props) {
        super(props)
        this.handleChange = this.handleChange.bind(this);
    }
    
    componentDidMount() {
        //this.setState({ temp: 0 });
    }
    componentDidUpdate(prevProps, prevState) {
    }

    convert_to_Array_of_Arrays(input, the_metric){
      var output = input.map(function(obj) {
          return [obj.dummy, obj.timeline, obj.wasNan, obj[the_metric]]
        }); 
      return output;  
    }

    handleChange(event){
        console.log(this.calculate_uniform_noise([1,3,5], event.target.value));
        var noise_control = this.props.noise_control;
        noise_control[this.props.the_metric] = event.target.value
        //this.props.set_noise_temperature_temp(event.target.value);
        this.props.set_noise_control(noise_control);

        var updated_metric =this.props.updated_metric;
        //var formatted_array = updated_metric[this.props.the_metric];
        var formatted_array = ((updated_metric[this.props.the_metric]).length === 0)?this.convert_to_Array_of_Arrays(this.props.the_data, this.props.the_metric):updated_metric[this.props.the_metric];
        //console.log("Initial",formatted_array);
        var formatted_array_edited = this.calculate_uniform_noise(formatted_array.map(em => em[3]),event.target.value);
        formatted_array = formatted_array.map((em,i) => [em[0], em[1], em[2],formatted_array_edited[i]])
        updated_metric[this.props.the_metric] = formatted_array;
        this.props.set_updated_metric(updated_metric);
        this.props.set_updated_metric_dummy(formatted_array);
        this.props.set_updated_temperature(formatted_array);
        //console.log(updated_metric[this.props.the_metric])
        if(this.props.url_version !== "1.3"){this.props.set_updated_temperature(formatted_array);}//doing this to trigger an update

        if(this.props.the_metric==="temperature"){this.props.set_updated_temperature(formatted_array);}
        else if(this.props.the_metric==="humidity"){this.props.set_updated_humidity(formatted_array);}
        else if(this.props.the_metric==="apparent_power"){this.props.set_updated_apparent_power(formatted_array);}
        //console.log("Final", formatted_array);
    }

    getRandomArbitrary(min, max) {
        return Math.random() * (max - min) + min;
      }

    calculate_uniform_noise(arr,noise){
        var lower_number = 1-(noise/100);//0.95;
        var upper_number = 1+(noise/100);//1.05
        var noisy_arr = arr.map((el)=>this.getRandomArbitrary(lower_number*el, upper_number*el));
        return noisy_arr;
    }

    render() {
        // css design is in App.css
        // Tutorial: https://mui.com/material-ui/react-select/

        return <FormControl sx={{ m: -0.5, minWidth: 70 }} size="small" variant="standard">
        {/* <InputLabel id="demo-select-small">Add Noise</InputLabel> */}
        <Select
           labelId={"demo-select-small_"+this.props.the_metric}
           id={"demo-select-small_"+this.props.the_metric}

          disabled={this.props.isLoadingUpdate}
          // value={this.props.noise_temperature_temp}
          value={this.props.noise_control[this.props.the_metric]}
          onChange={this.handleChange}
          input={<BootstrapInput />}
        >
        <MenuItem disabled value={-1}>
            Add Noise
          </MenuItem>
          {/* <MenuItem value={0}>
            <em>None</em>
          </MenuItem> */}
          <MenuItem value={5}>Uniform 5%</MenuItem>
          <MenuItem value={10}>Uniform 10%</MenuItem>
        </Select>
      </FormControl>
       
    
    }
  
};
const maptstateToprop = (state) => {
    return {
        blank_placeholder:state.blank_placeholder,
        url_version: state.url_version,
        isLoadingUpdate: state.isLoadingUpdate,
        noise_temperature_temp: state.noise_temperature_temp,
        updated_metric: state.updated_metric,
        noise_control: state.noise_control,
    }
}
const mapdispatchToprop = (dispatch) => {
    return {
        set_blank_placeholder: (val) => dispatch({ type: "blank_placeholder", value: val }),
        set_noise_temperature_temp: (val) => dispatch({ type: "noise_temperature_temp", value: val }),
        set_noise_control: (val) => dispatch({ type: "noise_control", value: val }),
        set_updated_temperature: (val) => dispatch({ type: "updated_temperature", value: val }),
        set_updated_humidity: (val) => dispatch({ type: "updated_humidity", value: val }),
        set_updated_apparent_power: (val) => dispatch({ type: "updated_apparent_power", value: val }),
        set_updated_metric: (val) => dispatch({ type: "updated_metric", value: val }),
        set_updated_metric_dummy: (val) => dispatch({ type: "updated_metric_dummy", value: val }),
    }
}
export default connect(maptstateToprop, mapdispatchToprop)(NoiseAdditionOption);