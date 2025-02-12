/* eslint-disable no-useless-constructor */
/* eslint-disable no-unused-vars */
import React, {Component} from 'react';
import { connect } from "react-redux";
import { Card, CardGroup} from 'react-bootstrap';
import Grid from '@mui/material/Grid';
import * as $ from "jquery";
import 'bootstrap/dist/css/bootstrap.min.css';
import Button from '@mui/material/Button';
import Sensitivity from '../charts/Sensitivity';
import Tooltip from '@mui/material/Tooltip';

export class  CardOne extends Component {
  //const classes = useStyles();
  constructor(props) {
    super(props);
    console.log();
  
}
componentDidMount() {}
componentDidUpdate() {}
shouldComponentUpdate(nextProps, nextState){
    return true
}





render(){ 
//const { selected_list } = this.state;  
return (
    <div>
    {(!this.props.enable_seasons_choice)?
      <Card style={{height: "90vh"}}>
      <Card.Header style={{opacity:(this.props.isLoadingUpdate)?0.4:1}}>
        <Grid container direction="row" spacing={1}>
        <Grid item xs={11} sm={11}>{"Sensitivity analysis by adding constant bias in temperature("+this.props.type+")"}</Grid>
        <Grid item xs={1} sm={1}>{(true)?<span style={{opacity:0}}><Button size="small"  color="secondary"  disabled={true}  style={{ backgroundColor: "#efefef", opacity: 1, borderRadius: 0, color: "black",  marginTop: -2, textTransform: 'none' }}
         >Update</Button></span>:null}</Grid>
        </Grid>
      </Card.Header>
      <Card.Body style={{opacity:(this.props.isLoadingUpdate)?0.4:1}}>
          {((this.props.mae_values).length >0)?<Sensitivity my_type={"no_season"} type={this.props.type}></Sensitivity>:null}
      </Card.Body>
      </Card>
      :
      null
      
    }  
    </div>
    
  );
 } //return ends
}

const maptstateToprop = (state) => {
  return {
      blank_placeholder: state.blank_placeholder,
      isLoadingUpdate: state.isLoadingUpdate,
      net_load_df: state.net_load_df,
      enable_seasons_choice: state.enable_seasons_choice,
      mae_values: state.mae_values,
  }
}
const mapdispatchToprop = (dispatch) => {
  return {
      set_blank_placeholder: (val) => dispatch({ type: "blank_placeholder", value: val }),
  }
}

export default connect(maptstateToprop, mapdispatchToprop)(CardOne);