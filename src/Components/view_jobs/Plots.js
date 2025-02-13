/* eslint-disable no-unused-vars */
/* eslint-disable array-callback-return */
import React, { Component } from 'react';
import { connect } from "react-redux";
import * as $ from "jquery";
import * as d3 from "d3";
import _ from 'lodash';
import Grid from '@mui/material/Grid';
//import fs from "fs";
//import * as fs from 'node:fs';
//import * as fs from 'node:fs/promises';







class Plots extends Component {
    constructor(props) {
        super(props)
        console.log();
        this.getTitle = this.getTitle.bind(this);
    }
    componentDidMount() {
        //this.setState({ temp: 0 });
        this.getTitle();
        this.plot_output_mae_multi(this.props.selected_job_name_sa, this.props.url, this.props.set_months_present_sa)
        this.plot_output_mape_multi(this.props.selected_job_name_sa, this.props.url)
        this.plotLegend(this.props.selected_job_name_sa, this.props.url)
    }
    componentDidUpdate(prevProps, prevState) {
        this.getTitle();
        this.plot_output_mae_multi(this.props.selected_job_name_sa, this.props.url, this.props.set_months_present_sa)
        this.plot_output_mape_multi(this.props.selected_job_name_sa, this.props.url)
        this.plotLegend(this.props.selected_job_name_sa, this.props.url)
    }

    getTitle(){
      var the_title = "Sensitivity Analysis";
      var self = this;
      d3.text(this.props.url+"/outputs/jobs/"+this.props.selected_job_name_sa+"/title.txt").then(function(data1){
        the_title = data1; 
        console.log(the_title);
        self.props.set_the_title_sa(the_title);
      })
    }

    plotLegend(selected_job_name_sa, url){
      
      var parent_width = $(".plots_container_parent").width()
      var parent_height = $(".plots_container_parent").height()
      console.log(parent_width, parent_height)
      var margin = {top: 0, right: 10, bottom: 0, left: 0},
      width = 0.10*parent_width - margin.left - margin.right,
      height = 0.65*parent_height - margin.top - margin.bottom;

      var svg = d3.select("#my_dataviz_svg_legend")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)

      var keys = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December", "Average"];
      const color = d3.scaleOrdinal()
                    .domain(keys)
                    .range(['#a6cee3','#1f78b4','#b2df8a','#33a02c','#fb9a99','#e31a1c','#fdbf6f','#ff7f00','#cab2d6','#6a3d9a','#ffff99','#b15928', '#000000']);
      
      var path1 = url+"/outputs/jobs/"+selected_job_name_sa+"/mae.csv";
      d3.csv(path1).then(
        function(data){
          var sumstat = d3.group(data, d => d.Month);
          var months_present_sa = Array.from(sumstat.keys());
          var keys_filtered = keys.filter(item => months_present_sa.includes(item))             


          svg.selectAll(".legend_dots").data(keys_filtered).join("circle").attr("class", "legend_dots")
          .attr("cx", 20)
          .attr("cy", function(d,i){ return 100 + i*25}) // 100 is where the first dot appears. 25 is the distance between dots
          .attr("r", 7)
          .style("fill", function(d){ return color(d)})
    
          svg.selectAll(".legend_text").data(keys_filtered).join("text").attr("class", "legend_text")
          .attr("x", 30)
          .attr("y", function(d,i){ return 100 + i*25}) // 100 is where the first dot appears. 25 is the distance between dots
          .style("fill", function(d){ return color(d)})
          .text(function(d){ return d})
          .attr("text-anchor", "left")
          .style("font-weight", (d)=>{return (d === "Average")?"bold":"normal"})
          .style("alignment-baseline", "middle")
        }
      )
      
            
      
    }

    plot_output_mae_multi(selected_job_name_sa, url, set_months_present_sa){
      var path1 = url+"/outputs/jobs/"+selected_job_name_sa+"/mae.csv"
      var path2 = url+"/outputs/jobs/"+selected_job_name_sa+"/mae_all.csv"
      // set the dimensions and margins of the graph
      var parent_width = $(".plots_container_parent").width()
      var parent_height = $(".plots_container_parent").height()
      console.log(parent_width, parent_height)
      var margin = {top: 40, right: 30, bottom: 45, left: 60},
      width = 0.45*parent_width - margin.left - margin.right,
      height = 0.65*parent_height - margin.top - margin.bottom;

      // append the svg object to the body of the page
      var svg1 = d3.select("#my_dataviz_svg_mae")
      //.append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      
      var svg = svg1.selectAll(".g_initial").data([0]).join("g").attr("class", "g_initial")
      .attr("transform", `translate(${margin.left},${margin.top})`);

      //svg.append("text")
      
      

      

      //Read the data
d3.csv(path1).then(

// Now I can use this dataset:
function(data) {
//console.log(data1);
// var the_title = "Sensitivity Analysis"
// d3.text(url+"/outputs/jobs/"+selected_job_name_sa+"/title.txt").then(function(data1){
//   the_title = data1; 
//   console.log(the_title);
//   svg.selectAll(".title_text").data([0]).join("text").attr("class", "title_text")
//       .attr("x", (width / 2))             
//       .attr("y", 0 - (margin.top / 2))
//       .attr("text-anchor", "middle")  
//       .style("font-size", "12px")  
//       .text(the_title);

// })


// Add X axis --> it is a date format
const x = d3.scaleLinear()
  .domain([0, 1.10*d3.max(data, function(d) { return +d.Noise_Percentage; })])
  .range([ 0, width ]); 

const xAxisTicks = x.ticks()
  .filter(tick => Number.isInteger(tick));  
//svg.append("g")
svg.selectAll(".g_x").data([0]).join("g").attr("class", "g_x")
  .attr("transform", `translate(0, ${height})`)
  .call(d3.axisBottom(x).tickValues(xAxisTicks).tickFormat(d=> d+"%"));

  svg.selectAll(".x_axis_label").data([0]).join("text").attr("class", "x_axis_label")
  //.append("text")
  //.attr("class", "x label")
  .attr("text-anchor", "end")
  .attr("x", width/1.8)
  .attr("y", height+40)
  .text("Noise Percentage(%)");

// Add Y axis
const y = d3.scaleLinear()
  .domain([0, 1.10*d3.max(data, function(d) { return +d.Mean_MAE; })])
  .range([ height, 0 ]);
svg.selectAll(".g_y").data([0]).join("g").attr("class", "g_y")
  //svg.append("g")
  .call(d3.axisLeft(y));

  svg.selectAll(".y_axis_label").data([0]).join("text").attr("class", "y_axis_label")
  //svg.append("text")
  //.attr("class", "y label")
  .attr("text-anchor", "end")
  .attr("y", -50)
  .attr("dy", ".75em")
  .attr("x", -height/2.2)
  .attr("transform", "rotate(-90)")
  .text("MAE(kW)");  

// Add the line
var sumstat = d3.group(data, d => d.Month);

const color = d3.scaleOrdinal()
    .domain(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December", "Average"])
    .range(['#a6cee3','#1f78b4','#b2df8a','#33a02c','#fb9a99','#e31a1c','#fdbf6f','#ff7f00','#cab2d6','#6a3d9a','#ffff99','#b15928', '#000000'])
 
//svg.append("path")
//svg.selectAll(".paths").data([0]).join("path").attr("class", "paths")
svg.selectAll(".paths").data(sumstat).join("path").attr("class", "paths")
  //.data(sumstat)
  .attr("fill", "none")
  .attr("stroke", (d)=>{return color(d[0])})
  .attr("stroke-width", (d)=>{return (d[0] === "Average")?4:1.5})
  .attr("d", function(d){
    return d3.line()
    .x(function(d) { return x(d.Noise_Percentage) })
    .y(function(d) { return y(d.Mean_MAE) })
    (d[1])
  }
    )

   
})

    }

    plot_output_mape_multi(selected_job_name_sa, url){
      var path1 = url+"/outputs/jobs/"+selected_job_name_sa+"/mape.csv"
      var path2 = url+"/outputs/jobs/"+selected_job_name_sa+"/mape_all.csv"
      // set the dimensions and margins of the graph
      var parent_width = $(".plots_container_parent").width()
      var parent_height = $(".plots_container_parent").height()
      console.log(parent_width, parent_height)
      var margin = {top: 40, right: 30, bottom: 45, left: 60},
      width = 0.45*parent_width - margin.left - margin.right,
      height = 0.65*parent_height - margin.top - margin.bottom;

      // append the svg object to the body of the page
      var svg1 = d3.select("#my_dataviz_svg_mape")
      //.append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      
      var svg = svg1.selectAll(".g_initial").data([0]).join("g").attr("class", "g_initial")
      .attr("transform", `translate(${margin.left},${margin.top})`);

      //svg.append("text")
      
      

      

      //Read the data
d3.csv(path1).then(

// Now I can use this dataset:
function(data) {
//console.log(data1);
// var the_title = "Sensitivity Analysis"
// d3.text(url+"/outputs/jobs/"+selected_job_name_sa+"/title.txt").then(function(data1){
//   the_title = data1; 
//   console.log(the_title);
//   svg.selectAll(".title_text").data([0]).join("text").attr("class", "title_text")
//       .attr("x", (width / 2))             
//       .attr("y", 0 - (margin.top / 2))
//       .attr("text-anchor", "middle")  
//       .style("font-size", "12px")  
//       .text(the_title);

// })


// Add X axis --> it is a date format
const x = d3.scaleLinear()
  .domain([0, 1.10*d3.max(data, function(d) { return +d.Noise_Percentage; })])
  .range([ 0, width ]); 

const xAxisTicks = x.ticks()
  .filter(tick => Number.isInteger(tick));  
//svg.append("g")
svg.selectAll(".g_x").data([0]).join("g").attr("class", "g_x")
  .attr("transform", `translate(0, ${height})`)
  .call(d3.axisBottom(x).tickValues(xAxisTicks).tickFormat(d=> d+"%"));

  svg.selectAll(".x_axis_label").data([0]).join("text").attr("class", "x_axis_label")
  //.append("text")
  //.attr("class", "x label")
  .attr("text-anchor", "end")
  .attr("x", width/1.8)
  .attr("y", height+40)
  .text("Noise Percentage(%)");

// Add Y axis
const y = d3.scaleLinear()
  .domain([0, 1.10*d3.max(data, function(d) { return +d.Mean_MAPE; })])
  .range([ height, 0 ]);
svg.selectAll(".g_y").data([0]).join("g").attr("class", "g_y")
  //svg.append("g")
  .call(d3.axisLeft(y));

  svg.selectAll(".y_axis_label").data([0]).join("text").attr("class", "y_axis_label")
  //svg.append("text")
  //.attr("class", "y label")
  .attr("text-anchor", "end")
  .attr("y", -50)
  .attr("dy", ".75em")
  .attr("x", -height/2.2)
  .attr("transform", "rotate(-90)")
  .text("MAPE (%)");  

// Add the line
var sumstat = d3.group(data, d => d.Month);
const color = d3.scaleOrdinal()
    .domain(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December", "Average"])
    .range(['#a6cee3','#1f78b4','#b2df8a','#33a02c','#fb9a99','#e31a1c','#fdbf6f','#ff7f00','#cab2d6','#6a3d9a','#ffff99','#b15928', '#000000'])
 
//svg.append("path")
//svg.selectAll(".paths").data([0]).join("path").attr("class", "paths")
svg.selectAll(".paths").data(sumstat).join("path").attr("class", "paths")
  //.data(sumstat)
  .attr("fill", "none")
  .attr("stroke", (d)=>{return color(d[0])})
  .attr("stroke-width", (d)=>{return (d[0] === "Average")?4:1.5})
  .attr("d", function(d){
    return d3.line()
    .x(function(d) { return x(d.Noise_Percentage) })
    .y(function(d) { return y(d.Mean_MAPE) })
    (d[1])
  }
    )

   
})

    }

    plot_output_mae(selected_job_name_sa, url){
        var path1 = url+"/outputs/jobs/"+selected_job_name_sa+"/mae.csv"
        var path2 = url+"/outputs/jobs/"+selected_job_name_sa+"/mae_all.csv"
        // set the dimensions and margins of the graph
        var parent_width = $(".plots_container_parent").width()
        var parent_height = $(".plots_container_parent").height()
        console.log(parent_width, parent_height)
        var margin = {top: 40, right: 30, bottom: 45, left: 60},
        width = 0.50*parent_width - margin.left - margin.right,
        height = 0.65*parent_height - margin.top - margin.bottom;

        // append the svg object to the body of the page
        var svg1 = d3.select("#my_dataviz_svg_mae")
        //.append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        
        var svg = svg1.selectAll(".g_initial").data([0]).join("g").attr("class", "g_initial")
        .attr("transform", `translate(${margin.left},${margin.top})`);

        //svg.append("text")
        
        

        

        //Read the data
d3.csv(path1).then(

// Now I can use this dataset:
function(data) {
  //console.log(data1);
  // var the_title = "Sensitivity Analysis"
  // d3.text(url+"/outputs/jobs/"+selected_job_name_sa+"/title.txt").then(function(data1){
  //   the_title = data1; 
  //   console.log(the_title);
  //   svg.selectAll(".title_text").data([0]).join("text").attr("class", "title_text")
  //       .attr("x", (width / 2))             
  //       .attr("y", 0 - (margin.top / 2))
  //       .attr("text-anchor", "middle")  
  //       .style("font-size", "12px")  
  //       .text(the_title);
  
  // })
  

  // Add X axis --> it is a date format
  const x = d3.scaleLinear()
    .domain([0, 1.10*d3.max(data, function(d) { return +d.Noise_Percentage; })])
    .range([ 0, width ]); 
  
  const xAxisTicks = x.ticks()
    .filter(tick => Number.isInteger(tick));  
  //svg.append("g")
  svg.selectAll(".g_x").data([0]).join("g").attr("class", "g_x")
    .attr("transform", `translate(0, ${height})`)
    .call(d3.axisBottom(x).tickValues(xAxisTicks).tickFormat(d=> d+"%"));

    svg.selectAll(".x_axis_label").data([0]).join("text").attr("class", "x_axis_label")
    //.append("text")
    //.attr("class", "x label")
    .attr("text-anchor", "end")
    .attr("x", width/1.8)
    .attr("y", height+40)
    .text("Noise Percentage(%)");

  // Add Y axis
  const y = d3.scaleLinear()
    .domain([0, 1.10*d3.max(data, function(d) { return +d.Mean_MAE; })])
    .range([ height, 0 ]);
  svg.selectAll(".g_y").data([0]).join("g").attr("class", "g_y")
    //svg.append("g")
    .call(d3.axisLeft(y));

    svg.selectAll(".y_axis_label").data([0]).join("text").attr("class", "y_axis_label")
    //svg.append("text")
    //.attr("class", "y label")
    .attr("text-anchor", "end")
    .attr("y", -50)
    .attr("dy", ".75em")
    .attr("x", -height/2.2)
    .attr("transform", "rotate(-90)")
    .text("MAE(kW)");  

  // Add the line
  //svg.append("path")
  svg.selectAll(".paths").data([0]).join("path").attr("class", "paths")
    .datum(data)
    .attr("fill", "none")
    .attr("stroke", "steelblue")
    .attr("stroke-width", 1.5)
    .attr("d", d3.line()
      .x(function(d) { return x(d.Noise_Percentage) })
      .y(function(d) { return y(d.Mean_MAE) })
      )

    d3.csv(path2).then(
        function(data2){
          var g_dots = svg.selectAll(".g_dots").data([0]).join("g").attr("class", "g_dots")
            //svg.append('g')
            g_dots.selectAll(".observation_dots").data(data2).join("circle").attr("class", "observation_dots")
                // .selectAll("dot")
                // .data(data2)
                // .enter()
                // .append("circle")
                .attr("cx", function (d) { return x(d.Noise_Percentage); } )
                .attr("cy", function (d) { return y(d.MAE); } )
                .attr("r", 2.5)
                .style("opacity", 0.6)
                .style("fill", "#69b3a2")
        }

    )  
})

    }
    plot_output_mape(selected_job_name_sa, url){
      var path1 = url+"/outputs/jobs/"+selected_job_name_sa+"/mape.csv"
      var path2 = url+"/outputs/jobs/"+selected_job_name_sa+"/mape_all.csv"
      // set the dimensions and margins of the graph
      var parent_width = $(".plots_container_parent").width()
      var parent_height = $(".plots_container_parent").height()
      console.log(parent_width, parent_height)
      var margin = {top: 40, right: 30, bottom: 45, left: 60},
      width = 0.50*parent_width - margin.left - margin.right,
      height = 0.65*parent_height - margin.top - margin.bottom;

      // append the svg object to the body of the page
      var svg1 = d3.select("#my_dataviz_svg_mape")
      //.append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      
      var svg = svg1.selectAll(".g_initial").data([0]).join("g").attr("class", "g_initial")
      .attr("transform", `translate(${margin.left},${margin.top})`);

      //svg.append("text")
      
      

      

      //Read the data
d3.csv(path1).then(

// Now I can use this dataset:
function(data) {
//console.log(data1);
// var the_title = "Sensitivity Analysis"
// d3.text(url+"/outputs/jobs/"+selected_job_name_sa+"/title.txt").then(function(data1){
//   the_title = data1; 
//   console.log(the_title);
//   svg.selectAll(".title_text").data([0]).join("text").attr("class", "title_text")
//       .attr("x", (width / 2))             
//       .attr("y", 0 - (margin.top / 2))
//       .attr("text-anchor", "middle")  
//       .style("font-size", "12px")  
//       .text(the_title);

// })


// Add X axis --> it is a date format
const x = d3.scaleLinear()
  .domain([0, 1.10*d3.max(data, function(d) { return +d.Noise_Percentage; })])
  .range([ 0, width ]); 

const xAxisTicks = x.ticks()
  .filter(tick => Number.isInteger(tick));  
//svg.append("g")
svg.selectAll(".g_x").data([0]).join("g").attr("class", "g_x")
  .attr("transform", `translate(0, ${height})`)
  .call(d3.axisBottom(x).tickValues(xAxisTicks).tickFormat(d=> d+"%"));

  svg.selectAll(".x_axis_label").data([0]).join("text").attr("class", "x_axis_label")
  //.append("text")
  //.attr("class", "x label")
  .attr("text-anchor", "end")
  .attr("x", width/1.8)
  .attr("y", height+40)
  .text("Noise Percentage(%)");

// Add Y axis
const y = d3.scaleLinear()
  .domain([0, 1.10*d3.max(data, function(d) { return +d.Mean_MAPE; })])
  .range([ height, 0 ]);
svg.selectAll(".g_y").data([0]).join("g").attr("class", "g_y")
  //svg.append("g")
  .call(d3.axisLeft(y));

  svg.selectAll(".y_axis_label").data([0]).join("text").attr("class", "y_axis_label")
  //svg.append("text")
  //.attr("class", "y label")
  .attr("text-anchor", "end")
  .attr("y", -50)
  .attr("dy", ".75em")
  .attr("x", -height/2.2)
  .attr("transform", "rotate(-90)")
  .text("MAPE (%)");  

// Add the line
//svg.append("path")
svg.selectAll(".paths").data([0]).join("path").attr("class", "paths")
  .datum(data)
  .attr("fill", "none")
  .attr("stroke", "steelblue")
  .attr("stroke-width", 1.5)
  .attr("d", d3.line()
    .x(function(d) { return x(d.Noise_Percentage) })
    .y(function(d) { return y(d.Mean_MAPE) })
    )

  d3.csv(path2).then(
      function(data2){
        var g_dots = svg.selectAll(".g_dots").data([0]).join("g").attr("class", "g_dots")
          //svg.append('g')
          g_dots.selectAll(".observation_dots").data(data2).join("circle").attr("class", "observation_dots")
              // .selectAll("dot")
              // .data(data2)
              // .enter()
              // .append("circle")
              .attr("cx", function (d) { return x(d.Noise_Percentage); } )
              .attr("cy", function (d) { return y(d.MAPE); } )
              .attr("r", 2.5)
              .style("opacity", 0.6)
              .style("fill", "#69b3a2")
      }

  )  
})

  }
    render() {
        // css design is in App.css

        return <div>
          <Grid container direction="column" alignItems="center" width="80vw">
            <Grid item >
              {this.props.the_title_sa}</Grid>
          </Grid>
        <div id="my_dataviz" className="plots_container_parent" style={{width:"80vw", height:"95vh"}}>
            <svg id="my_dataviz_svg_mae"></svg>
            <svg id="my_dataviz_svg_mape"></svg>
            <svg id="my_dataviz_svg_legend"></svg>
            <svg id="my_dataviz_svg_monthly"></svg>
        </div>
      </div>
       
    }
  
};
const maptstateToprop = (state) => {
    return {
        blank_placeholder:state.blank_placeholder,
        selected_job_name_sa: state.selected_job_name_sa,
        url: state.url,
        the_title_sa: state.the_title_sa,
    }
}
const mapdispatchToprop = (dispatch) => {
    return {
        set_blank_placeholder: (val) => dispatch({ type: "blank_placeholder", value: val }),
        set_the_title_sa: (val) => dispatch({ type: "the_title_sa", value: val }),
    }
}
export default connect(maptstateToprop, mapdispatchToprop)(Plots);