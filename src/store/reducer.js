var url_version = "1.3";

let initialState = {
    blank_placeholder: null,
    url: "http://localhost:5000",
    url_version : url_version,
    start_date: 1578009600000, // 1588291200000, // https://www.epochconverter.com/ (Use the timestamp in milliseconds)
    end_date: 1578096000000,//1578182400000,//1588464000000,
    start_date_temp: 1578009600000,//1588291200000,
    end_date_temp: 1578096000000,//1578182400000,//1588464000000,
    isLoadingUpdate: false,
    color_buttons: {"general": "rgb(224,224,224)", "focused": "rgb(108, 117, 125)"},
    actual_net_load: [],
    predicted_net_load: [],
    apparent_power: [],
    humidity: [],
    temperature: [],
    net_load_df: [],
    conf_95_df: [],
    net_load_df_old: [],
    conf_95_df_old: [],
    temperature_df: [],
    humidity_df: [],
    apparent_power_df: [],
    input_variable_df_safe:{},
    temperature_nans_percentage: 0,
    humidity_nans_percentage: 0,
    apparent_power_nans_percentage: 0,
    nans_dict_percentage: {},
    solar_penetration_temp: (url_version === "1.3")?50:20,
    solar_penetration: (url_version === "1.3")?50:20,
    temp_check: (url_version === "1.3")?{"temperature":[], "humidity":[], "apparent_power":[]}:{"SZA":[], "AZM":[], "ETR":[], "GHI":[], "Wind_Speed":[], "Temperature":[]},
    updated_temperature:[],
    updated_humidity:[],
    updated_apparent_power:[], // need to keep this to trigger an update
    updated_metric:(url_version === "1.3")?{"temperature":[], "humidity":[], "apparent_power":[]}:{"SZA":[], "AZM":[], "ETR":[], "GHI":[], "Wind_Speed":[], "Temperature":[]},
    updated_metric_dummy:[],
    enable_seasons_flag:0,
    enable_seasons_choice_temp:0,
    enable_seasons_choice:0,
    noise_temperature_temp: -1,
    noise_temperature:-1,
    noise_control:(url_version === "1.3")?{"temperature":-1, "humidity":-1, "apparent_power":-1}:{"SZA":-1, "AZM":-1, "ETR":-1, "GHI":-1, "Wind_Speed":-1, "Temperature":-1},
    mae:0,
    mape:0,
    mean_ape:0,
    median_ape:0,
    mode_ape:0,
    mae_values:[],
    mape_values:[],
    freezed_axis:[],
    current_net_load_y_axis: [],
    selected_model:"15 min ahead",
    selected_variables_temp:(url_version === "1.3")?["temperature", "humidity", "apparent_power"]:["SZA", "AZM", "ETR", "GHI", "Wind_Speed", "Temperature"],
    selected_variables: (url_version === "1.3")?["temperature", "humidity", "apparent_power"]:["SZA", "AZM", "ETR", "GHI", "Wind_Speed", "Temperature"],
    selected_variables_unit: (url_version === "1.3")?{"temperature":" (°F)", "humidity":" (%)", "apparent_power":" (kVA)"}:{"SZA":" (°)", "AZM":" (°)", "ETR":" (W/m^2)", "GHI":" (W/m^2)", "Wind_Speed":" (m/s)", "Temperature":" (°C)"},
    // SZA: Solar Zenith Angle; AZM: Azimuth angle; ETR: ExtraTerrestial Irradiance; GHI: Global Horizontal Irradiance; Wind Speed is meters/seconds as per the user guide;
    selected_card_sensitivity_analysis: "create_job",
    input_variable_sa: "temperature",
    start_date_sa: "Start Date",
    end_date_sa: "End Date",
    months_sa: [],
    noise_direction_sa: "bidirectional",
    noise_level_sa: "None",
    number_of_observations_sa: "None",
    name_sa: "",
    description_sa: "",
    created_jobs_name_sa: [],
    selected_job_name_sa: "sample1",
    is_job_ready_sa: false,
    the_title_sa: "Sensitivity Analysis",
    animation_duration: 2500,
}

const reducer = (state = initialState, action) => {
    if (action.type === "blank_placeholder") {
        return {...state, blank_placeholder: action.value}
    }
    if (action.type === "start_date") {
        return {...state, start_date: action.value}
    }
    if (action.type === "end_date") {
        return {...state, end_date: action.value}
    }
    if (action.type === "start_date_temp") {
        return {...state, start_date_temp: action.value}
    }
    if (action.type === "end_date_temp") {
        return {...state, end_date_temp: action.value}
    }
    if (action.type === "isLoadingUpdate") {
        return { ...state, isLoadingUpdate: action.value }
     }
    if (action.type === "actual_net_load") {
        return { ...state, actual_net_load: action.value }
     } 
    if (action.type === "predicted_net_load") {
        return { ...state, predicted_net_load: action.value }
     }
    if (action.type === "apparent_power") {
        return { ...state, apparent_power: action.value }
     }
    if (action.type === "humidity") {
        return { ...state, humidity: action.value }
     }
    if (action.type === "temperature") {
        return { ...state, temperature: action.value }
     }
    if (action.type === "net_load_df") {
        return { ...state, net_load_df: action.value }
     }
     if (action.type === "net_load_df_old") {
        return { ...state, net_load_df_old: action.value }
     }
    if (action.type === "temperature_df") {
        return { ...state, temperature_df: action.value }
     } 
    if (action.type === "humidity_df") {
        return { ...state, humidity_df: action.value }
     } 
    if (action.type === "apparent_power_df") {
        return { ...state, apparent_power_df: action.value }
     } 
    if (action.type === "input_variable_df") {
        return { ...state, input_variable_df: action.value }
     }
    if (action.type === "temperature_nans_percentage") {
        return { ...state, temperature_nans_percentage: action.value }
     } 
    if (action.type === "humidity_nans_percentage") {
        return { ...state, humidity_nans_percentage: action.value }
     } 
    if (action.type === "apparent_power_nans_percentage") {
        return { ...state, apparent_power_nans_percentage: action.value }
     }
    if (action.type === "nans_dict_percentage") {
        return { ...state, nans_dict_percentage: action.value }
    }
    if (action.type === "solar_penetration_temp") {
        return { ...state, solar_penetration_temp: action.value }
    } 
    if (action.type === "solar_penetration") {
        return { ...state, solar_penetration: action.value }
     }
    if (action.type === "temp_check") {
        return { ...state, temp_check: action.value }
    }  
    if (action.type === "updated_temperature") {
        return { ...state, updated_temperature: action.value }
    }
    if (action.type === "updated_humidity") {
        return { ...state, updated_humidity: action.value }
    }
    if (action.type === "updated_apparent_power") {
        return { ...state, updated_apparent_power: action.value }
    }
    if (action.type === "updated_metric") {
        return { ...state, updated_metric: action.value }
    }
    if (action.type === "updated_metric_dummy") {
        return { ...state, updated_metric_dummy: action.value }
    }
    if (action.type === "enable_seasons_flag") {
        return { ...state, enable_seasons_flag: action.value }
    } 
    if (action.type === "enable_seasons_choice_temp") {
        return { ...state, enable_seasons_choice_temp: action.value }
    } 
    if (action.type === "enable_seasons_choice") {
        return { ...state, enable_seasons_choice: action.value }
    } 
    if (action.type === "conf_95_df") {
        return { ...state, conf_95_df: action.value }
    }
    if (action.type === "conf_95_df_old") {
        return { ...state, conf_95_df_old: action.value }
    }
    if (action.type === "noise_temperature_temp") {
        return { ...state, noise_temperature_temp: action.value }
    }
    if (action.type === "noise_temperature") {
        return { ...state, noise_temperature: action.value }
    }
    if (action.type === "noise_control") {
        return { ...state, noise_control: action.value }
    }
    if (action.type === "mae") {
        return { ...state, mae: action.value }
    }
    if (action.type === "mape") {
        return { ...state, mape: action.value }
    } 
    if (action.type === "mean_ape") {
        return { ...state, mean_ape: action.value }
    }
    if (action.type === "median_ape") {
        return { ...state, median_ape: action.value }
    }
    if (action.type === "mode_ape") {
        return { ...state, mode_ape: action.value }
    }  
    if (action.type === "mape_values") {
        return { ...state, mape_values: action.value }
    }
    if (action.type === "freezed_axis") {
        return { ...state, freezed_axis: action.value }
    } 
    if (action.type === "current_net_load_y_axis") {
        return { ...state, current_net_load_y_axis: action.value }
    } 
    if (action.type === "selected_model") {
        return { ...state, selected_model: action.value }
    }
    if (action.type === "selected_variables_temp") {
        return { ...state, selected_variables_temp: action.value }
    }
    if (action.type === "selected_variables") {
        return { ...state, selected_variables: action.value }
    } 
    if (action.type === "animation_duration") {
        return { ...state, animation_duration: action.value }
    }  
    if (action.type === "selected_card_sensitivity_analysis") {
        return { ...state, selected_card_sensitivity_analysis: action.value }
    }
    if (action.type === "input_variable_sa") {
        return { ...state, input_variable_sa: action.value }
    }
    if (action.type === "start_date_sa") {
        return { ...state, start_date_sa: action.value }
    }
    if (action.type === "end_date_sa") {
        return { ...state, end_date_sa: action.value }
    }
    if (action.type === "months_sa") {
        return { ...state, months_sa: action.value }
    }
    if (action.type === "noise_direction_sa") {
        return { ...state, noise_direction_sa: action.value }
    }
    if (action.type === "noise_level_sa") {
        return { ...state, noise_level_sa: action.value }
    }
    if (action.type === "number_of_observations_sa") {
        return { ...state, number_of_observations_sa: action.value }
    }
    if (action.type === "name_sa") {
        return { ...state, name_sa: action.value }
    }
    if (action.type === "description_sa") {
        return { ...state, description_sa: action.value }
    }
    if (action.type === "created_jobs_name_sa") {
        return { ...state, created_jobs_name_sa: action.value }
    }
    if (action.type === "selected_job_name_sa") {
        return { ...state, selected_job_name_sa: action.value }
    }  
    if (action.type === "is_job_ready_sa") {
        return { ...state, is_job_ready_sa: action.value }
    } 
    if (action.type === "the_title_sa") {
        return { ...state, the_title_sa: action.value }
    }
           

    return state;
}

export default reducer;