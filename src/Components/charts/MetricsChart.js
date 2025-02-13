/* eslint-disable no-unused-vars */
/* eslint-disable array-callback-return */
import React, { Component } from 'react';
import { connect } from "react-redux";
import * as $ from "jquery";
import * as d3 from "d3";
import _ from 'lodash';

var tooltip;

class MetricsChart extends Component {
    constructor(props) {
        super(props)
        console.log();

    }
    componentDidMount() {
        //this.setState({ temp: 0 });
        this.create_line_chart(this.props.the_data, this.props.the_metric);
    }
    componentDidUpdate(prevProps, prevState) {
        this.create_line_chart(this.props.the_data, this.props.the_metric);
    }

    roundToNearest15(date = new Date()) {
        const minutes = 15;
        const ms = 1000 * 60 * minutes;
      
        return new Date(Math.floor(date.getTime() / ms) * ms);
      }
    convert_to_Array_of_Arrays(input, the_metric){
        var output = input.map(function(obj) {
            return [obj.dummy, obj.timeline, obj.wasNan, obj[the_metric]]
          });
        return output;  
    }  

    create_line_chart(the_data, the_metric){
        var self = this;
        var animation_duration = 2000;
        var the_id = "#metricChartDiv_"+the_metric;   
        const margin = {top: 10, right: 30, bottom: 30, left: 60},
        width = $(the_id).width() - margin.left - margin.right,
        height = $(the_id).height() - margin.top - margin.bottom;

        var formatted_array = this.convert_to_Array_of_Arrays(the_data, the_metric);
        console.log(formatted_array);

        //the_data = the_data.filter((d) => d.temperature !== 99999); // removing NaN

        /** svg1 just sets the width and height of the svg */
        //$(".netLoadChart").empty();
        const svg1 = d3.select(".metricChart_"+the_metric)
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        /** This adds a g to control the margin of the svg */
        var svg = d3.select(".metricChart_"+the_metric).selectAll(".initial_g_metric_"+the_metric).data([0]).join("g")
        .attr("class", "initial_g_metric_"+the_metric)    
        .attr("transform",`translate(${margin.left},${margin.top})`);


        /** Grouping the data: in order to draw one line per group */
        var sumstat2 = (((this.props.temp_check)[the_metric]).length === 0)?(d3.group(the_data, d => d.dummy)):((this.props.temp_check)[the_metric]) // group function allows to group the calculation per level of a factor

        /** Adding and calling X axis --> it is a date format */
        var starting_date = the_data[0]["timeline"]
        var ending_date = the_data[the_data.length -1]["timeline"]
        //console.log(starting_date, ending_date)
        const x = d3.scaleTime()
        //.domain(d3.extent(net_load_df, function(d) { return d.years; }))
        .domain([new Date(starting_date), new Date(ending_date)])
        .range([ 0, width ]); // can add .nice() to force the last tick
        svg.selectAll(".g_X_metric_"+the_metric).data([0]).join("g")
        .attr("class", "g_X_metric_"+the_metric)  
        .attr("transform", `translate(0, ${height})`)
        .transition()
        .duration(animation_duration)
        .call(d3.axisBottom(x)); //removed the ticks

        /** Adding and calling Y axis */ 
        //var limit = 1.1*(Math.max(Math.abs(d3.min(the_data, function(d) { return temperature; })), Math.abs(d3.max(net_load_df, function(d) { return d.net_load; }))))
        var upper_limit = 1.1*d3.max(the_data,(d) => d[the_metric]);
        var lower_limit = 0.9*d3.min(the_data,(d) => d[the_metric]);
        const y = d3.scaleLinear()
        .domain([lower_limit,upper_limit])
        .range([ height, 0 ]);
        svg.selectAll(".g_Y_metric_"+the_metric).data([0]).join("g")
        .attr("class", "g_Y_metric_"+the_metric)
        .transition()
        .duration(animation_duration)
        .call(d3.axisLeft(y));

        /** Color palette */ 
        const color = d3.scaleOrdinal()
        //.range(['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999'])
        .range(["#377eb8"]);

        
        function dragstarted(d) {
            d3.select(this).raise().classed('active', true);
        }
        
        function dragged(event, d) {
            d[0] = self.roundToNearest15(x.invert(event.x)); //this.roundToNearest15(x.invert(event.x))
            d[1] = y.invert(event.y);
            d3.select(this)
                .attr('cx', x(d[0]))
                .attr('cy', y(d[1]))
            // need to update net_load_df and then sumstat2   
            var edited_timeline = (d[0].toISOString()).replace("T", " ").replace(".000Z", "");
            //console.log(edited_timeline);
            var obj = the_data.find(f=>f.timeline===edited_timeline);
            if(obj){obj.net_load=d[1];}
            sumstat2 =  d3.group(the_data, d => d.dummy);
            console.log(edited_timeline, sumstat2);
            
            // svg.selectAll(".lineCharts_metric_"+the_metric).data(sumstat2).join("path").attr("class", "lineCharts_metric_"+the_metric).attr("fill", "none")
            // .attr("stroke", function(d){return "url(#line-gradient_"+the_metric+")" })
            // .attr("stroke-width", 1.5)
            // .attr('d',  function(d){
            //     return d3.line()
            //         .curve(d3.curveStep)
            //         .x(function(d) { return x(new Date(d.timeline)); })
            //         .y(function(d) { return y(d[the_metric]); })
            //         (d[1])
            //     });
        }
        
        function dragended(d) {
            d3.select(this).classed('active', false);
            var tempo = {...self.props.temp_check};
            tempo[the_metric] = sumstat2;
            self.props.set_temp_check(tempo);
        }
        var drag = d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended);

        /** Drawing the lines */ 
            // Set the gradient
            svg.selectAll(".linearGradient_"+the_metric)
            .data([0])
            .join("linearGradient")
            .attr("class", "linearGradient_"+the_metric)
            .attr("id", "line-gradient_"+the_metric)
            .attr("gradientUnits", "userSpaceOnUse")
            .attr("x1", 0)
            .attr("x2", width)
            .selectAll("stop")
            .data(the_data)
            .join("stop")
            .attr("offset", function(d) { return x(new Date(d.timeline))/width; })
            .attr("stop-color", function(d) { return (d.wasNan)?"red":"#377eb8"; });

            svg.selectAll(".lineCharts_metric_"+the_metric)
            .data(sumstat2)
            //.data(the_data, (d)=>[d.net_load, d.dummy, d.timeline, d.wasNan])
            .join("path")
            .attr("class", "lineCharts_metric_"+the_metric)
            .attr("fill", "none")
            .attr("stroke", function(d){return "url(#line-gradient_"+the_metric+")" })
            .attr("stroke-width", 1.5)
            //.on("mousemove", (event)=>{console.log(this.roundToNearest15(x.invert(d3.pointer(event)[0])))})
            .transition()
            .duration(animation_duration)
            .attr("d", function(d){
            return d3.line()
                .curve(d3.curveStep)
                .x(function(d) { return x(new Date(d.timeline)); })
                .y(function(d) { return y(d[the_metric]); })
                (d[1])
            }) 
            //.attr("stroke-linejoin", "arcs")
            //.attr("stroke-linecap", "round") 
            
            svg.selectAll('.my_circles_'+the_metric)
                .data(the_data, (d)=>[d.net_load, d.dummy, d.timeline, d.wasNan])
                .join("circle")
                .attr("class", "my_circles_"+the_metric)
                .attr('r', 1.0)
                .attr('cx', function(d) { return x(new Date(d.timeline));  }) 
                .attr('cy', function(d) { return y(d[the_metric]); }) 
                .style('cursor', 'pointer')
                .style('fill', 'steelblue');

            svg.selectAll('.my_circles_'+the_metric)
                        .call(drag);

            // info icon about missing data
            d3.selectAll(".metrics_nans_info_icon_"+the_metric).on("mouseover", function (event) {
                tooltip.transition()
                  .duration(200)
                  .style("opacity", .9);
                tooltip.html("Missing data: "+String(self.props.the_nans_percentage)+"% <br> These are interpolated and marked in <span style='color: red; font-weight:bold'>red</span>")
                  .style("left", (event.pageX + 5) + "px")
                  .style("top", (event.pageY - 10) + "px");
              })
                .on("mouseout", function (d) {
                  tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
                })

    }
    render() {
        // css design is in App.css
        tooltip = d3.select("body").selectAll(".tooltip_matches").data([0]).join('div')
            .attr("class", "tooltip_matches")
            .style("opacity", 0);

        return <div>
        <div id={"metricChartDiv_"+this.props.the_metric} style={{height:"25vh"}}>
        <svg className={"metricChart_"+this.props.the_metric}></svg>
        </div>
      </div>
       
    }
  
};
const maptstateToprop = (state) => {
    return {
        blank_placeholder:state.blank_placeholder,
        net_load_df: state.net_load_df,
        temp_check: state.temp_check,
    }
}
const mapdispatchToprop = (dispatch) => {
    return {
        set_blank_placeholder: (val) => dispatch({ type: "blank_placeholder", value: val }),
        set_temp_check: (val) => dispatch({ type: "temp_check", value: val }),
    }
}
export default connect(maptstateToprop, mapdispatchToprop)(MetricsChart);