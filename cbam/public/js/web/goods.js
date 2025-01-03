frappe.provide("cbam.goods")

$.extend(cbam.goods, {
    submit_goods(goods){
        if (!Array.isArray(goods)){
            goods = [goods]
        }
        frappe.call({
            method: "cbam.utils.goods.submit_goods",
            args:{
                goods: goods
            },
            callback(r){
                msgprint("Goods Submitted Successfully.")
            }
        })
    },
    forward_goods(supplier, goods){
        if(!Array.isArray(goods)){
            goods = [goods]
        }
        frappe.call({
            method: "cbam.utils.goods.forward_goods",
            args:{
                goods: goods,
                supplier: supplier
            },
            callback(){
                msgprint("Goods forwarded.")
              } 
        })
    },
    reject_goods(goods, reason){
        if(!Array.isArray(goods)){
            goods = [goods]
        }
        frappe.call({
            method: "cbam.utils.goods.reject_goods",
            args:{
                goods: goods,
                reason: reason
            },
            callback(){
                msgprint("Goods Rejected.")
              } 
        })
    },
    assign_emission(emission, goods){
        frappe.call({
            method: "cbam.utils.goods.assign_emission",
            args:{
                emission: emission,
                goods: goods
            },
            freeze: true,
            freeze_message: `Assigning Emissions, please wait....`,
            callback(){
                msgprint("Emissions assigned successfully.")
            }

        })
    },
    split_goods(good, values){
        frappe.call({
            method: "cbam.utils.goods.split_goods",
            args:{
                good: good,
                values: values
            },
            freeze: true,
            freeze_message: `Splitting Goods, please wait....`,
            callback(){
                msgprint("Goods Split successfully.")
            }

        })
    }
})